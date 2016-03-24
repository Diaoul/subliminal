# -*- coding: utf-8 -*-
import io
import json
import logging
import os
import re

from babelfish import Language, language_converters
from guessit import guessit
from rarfile import RarFile, is_rarfile
from requests import Session
from zipfile import ZipFile, is_zipfile

from . import ParserBeautifulSoup, Provider
from .. import __short_version__
from ..cache import region, EPISODE_EXPIRATION_TIME, SHOW_EXPIRATION_TIME
from ..exceptions import AuthenticationError, ConfigurationError
from ..subtitle import Subtitle, fix_line_ending, guess_matches, sanitize, SUBTITLE_EXTENSIONS
from ..video import Episode, Movie

TIMEOUT = 10

logger = logging.getLogger(__name__)

language_converters.register('legendastv = subliminal.converters.legendastv:LegendasTvConverter')


class LegendasTvSubtitle(Subtitle):
    provider_name = 'legendastv'

    def __init__(self, language, page_link, subtitle_id, name, binary_content, imdb_id=None, type=None, season=None,
                 year=None, no_downloads=None, rating=None, featured=False, multiple_episodes=False, timestamp=None):
        super(LegendasTvSubtitle, self).__init__(language, page_link=page_link)
        self.subtitle_id = subtitle_id
        self.name = name
        self.imdb_id = imdb_id
        self.type = type
        self.season = season
        self.year = year
        self.no_downloads = no_downloads
        self.rating = rating
        self.featured = featured
        self.multiple_episodes = multiple_episodes
        self.timestamp = timestamp
        self.binary_content = binary_content

    @property
    def id(self):
        return '%s-%s' % (self.subtitle_id, self.name.lower())

    def get_matches(self, video, hearing_impaired=False):
        matches = set()

        # The best available information about a subtitle is its name. Using guessit to parse it.
        guess = guessit(self.name, {'type': self.type})
        matches |= guess_matches(video, guess)

        # imdb_id match used only for movies
        if self.type == 'movie' and video.imdb_id and self.imdb_id == video.imdb_id:
            matches.add('imdb_id')

        return matches


class LegendasTvProvider(Provider):
    languages = {Language.fromlegendastv(l) for l in language_converters['legendastv'].codes}
    video_types = (Episode, Movie)
    server_url = 'http://legendas.tv'

    def __init__(self, username=None, password=None):
        if username is not None and password is None or username is None and password is not None:
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.logged_in = False

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__

        # login
        if self.username is not None and self.password is not None:
            logger.info('Logging in')
            data = {'_method': 'POST', 'data[User][username]': self.username, 'data[User][password]': self.password}
            r = self.session.post('%s/login' % self.server_url, data, allow_redirects=False, timeout=TIMEOUT)
            r.raise_for_status()

            soup = ParserBeautifulSoup(r.content, ['html.parser'])
            auth_error = soup.find('div', {'class': 'alert-error'}, text=re.compile(u'.*Usuário ou senha inválidos.*'))

            if auth_error:
                raise AuthenticationError(self.username)

            logger.debug('Logged in')
            self.logged_in = True

    def terminate(self):
        # logout
        if self.logged_in:
            logger.info('Logging out')
            r = self.session.get('%s/users/logout' % self.server_url, timeout=TIMEOUT)
            r.raise_for_status()
            logger.debug('Logged out')
            self.logged_in = False

        self.session.close()

    def matches(self, actual_properties, expected_title, expected_season=None, expected_episode=None,
                expected_year=None, ignore_episode=False):
        """
        Matches the `actual_properties` against the expected parameters. The `actual_properties` keys follow the
        guessit properties names.
        For movies:
          - `type` should match
          - `title` should match
          - `year` should match, unless they're not defined and expected and actual `title`s are equal
        For episodes:
          - `type` should match
          - `series` should match
          - `season` should match
          - `episode` should match, unless `ignore_episode` is True

        :param dict actual_properties: dictionary that contains the actual values following guessit property names.
        :param str expected_title: the expected movie/series title.
        :param int expected_season: the expected series season number.
        :param int expected_episode: the expected series episode number.
        :param int expected_year: the expected movie/series year.
        :param bool ignore_episode: `True` if episode matching should be ignored. Default: `False`.
        :return: Whether actual matches expected.
        :rtype: bool

        """
        expected_type = 'episode' if expected_season else 'movie'
        if expected_type != actual_properties.get('type'):
            return False

        s_actual_title = sanitize(actual_properties.get('title'))
        s_expected_title = sanitize(expected_title)

        if not s_actual_title or not s_expected_title or s_expected_title not in s_actual_title:
            return False

        if expected_type == 'movie':
            if expected_year != actual_properties.get('year'):
                if expected_year and actual_properties.get('year'):
                    return False
                if s_expected_title != s_actual_title:
                    return False

        elif expected_type == 'episode':
            if expected_season != actual_properties.get('season'):
                return False
            if not ignore_episode and expected_episode != actual_properties.get('episode'):
                return False

        return True

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search_candidates(self, title, season, episode, year):
        """
        Returns candidates for shows or movies by querying `/legenda/sugestao` page.
        Since the result is a list of candidates (movies, series, etc) an additional filtering is required.
        The properties type, name, year and season are used to filter out bad suggestions.

        :param str title: the movie/series title.
        :param int season: the series season number.
        :param int episode: the series episode number.
        :param int year: the movie/series year.
        :return: the candidates for shows or movies.
        :rtype: list of dict

        """
        # get the shows/movies out of the suggestions.
        # json sample:
        # [
        #    {
        #        "_index": "filmes",
        #        "_type": "filme",
        #        "_id": "24551",
        #        "_score": null,
        #        "_source": {
        #            "id_filme": "24551",
        #            "id_imdb": "903747",
        #            "tipo": "S",
        #            "int_genero": "1036",
        #            "dsc_imagen": "tt903747.jpg",
        #            "dsc_nome": "Breaking Bad",
        #            "dsc_sinopse": "Dos mesmos criadores de Arquivo X, mas n\u00e3o tem nada de sobrenatural nesta
        #                            s\u00e9rie. A express\u00e3o \"breaking bad\" \u00e9 usada quando uma coisa que
        #                            j\u00e1 estava ruim, fica ainda pior. E \u00e9 exatamente isso que acontece com
        #                            Walter White, um professor de qu\u00edmica, que vivia sua vida \"tranquilamente\"
        #                            quando, boom, um diagn\u00f3stico terminal muda tudo. O liberta. Ele come\u00e7a a
        #                            usar suas habilidades em qu\u00edmica de outra forma: montando um laborat\u00f3rio
        #                            de drogas para financiar o futuro de sua fam\u00edlia.",
        #            "dsc_data_lancamento": "2011",
        #            "dsc_url_imdb": "http:\/\/www.imdb.com\/title\/tt0903747\/",
        #            "dsc_nome_br": "Breaking Bad - 4\u00aa Temporada",
        #            "soundex": null,
        #            "temporada": "4",
        #            "id_usuario": "241436",
        #            "flg_liberado": "0",
        #            "dsc_data_liberacao": null,
        #            "dsc_data": "2011-06-12T21:06:42",
        #            "dsc_metaphone_us": "BRKNKBT0SSN",
        #            "dsc_metaphone_br": "BRKNKBTTMPRT",
        #            "episodios": null,
        #            "flg_seriado": null,
        #            "last_used": "1372569074",
        #            "deleted": false
        #        },
        #        "sort": [
        #            "4"
        #        ]
        #    }
        # ]
        #
        # Notes:
        #  tipo: Defines if the entry is a movie or a tv show (or a collection??)
        #  imdb_id: Sometimes it appears as a number and sometimes as a string prefixed with tt
        #  temporada: Sometimes is ``null`` and season information should be extracted from dsc_nome_br

        # /legenda/sugestao endpoint:
        #   - doesn't accept titles with colon
        #   - doesn't ignore single quotes
        keywords = {k.lower().replace(':', '') for k in [title,  title.replace('\'', '')]}
        results = dict()

        for keyword in keywords:
            logger.info('Searching candidates using the keyword %s', keyword)
            r = self.session.get('%s/legenda/sugestao/%s' % (self.server_url, keyword), timeout=TIMEOUT)
            r.raise_for_status()
            results.update({item['_id']: item for item in json.loads(r.text)})

        # type, title, series, season, year: should follow guessit properties names
        mapping = dict(
            id='id_filme',
            type='tipo',
            title='dsc_nome',
            series='dsc_nome',
            season='temporada',
            year='dsc_data_lancamento',
            title_br='dsc_nome_br',
            imdb_id='id_imdb'
        )

        # movie, episode: should follow guessit type values
        type_map = {
            'M': 'movie',
            'S': 'episode',
            'C': 'episode'  # Considering C as episode. Probably C stands for Collections
        }

        # Regex to extract the season number. e.g.: 3\u00aa Temporada, 1a Temporada, 2nd Season
        season_re = re.compile('.*? - (\d{1,2}).*?((emporada)|(season))', re.IGNORECASE)

        # Regex to extract the IMDB id. e.g.: tt02342
        imdb_re = re.compile('t{0,2}(\d+)')

        candidates = []
        for result in results.values():
            entry = result['_source']
            item = {k: entry.get(v) for k, v in mapping.items()}
            item['type'] = type_map.get(item.get('type'), 'movie')
            imdb_match = imdb_re.search(item.get('imdb_id'))
            item['imdb_id'] = imdb_match.group(1) if imdb_match else None

            # Season information might be missing and it should be extracted from 'title_br'
            if not item.get('season') and item.get('title_br'):
                season_match = season_re.search(item.get('title_br'))
                item['season'] = season_match.group(1) if season_match else None

            # Some string fields are actually integers
            for field in ['season', 'year', 'imdb_id']:
                field_text = item.get(field)
                item[field] = int(field_text) if field_text and field_text.isdigit() else None

            # ignoring episode match since this first step is only about movie/season information
            if self.matches(item, title, expected_season=season, expected_episode=episode, expected_year=year,
                            ignore_episode=True):
                candidates.append(dict(item))

        logger.debug('Candidates found: %s', candidates)
        return candidates

    def query(self, language, title, season=None, episode=None, year=None):
        """
        Returns a list of subtitles based on the input parameters.
          - 1st step: initial lookup for the movie/show information (see `search_candidates`)
          - 2nd step: list all candidates to movies/shows from previous step
          - 3rd step: reject candidates that doesn't match the input parameters (wrong season, wrong episode, etc...)
          - 4th step: download all subtitles to inspect the 'release name'
          - 5th step: creates a subtitle for each release

        :param language: the requested language
        :param str title: the movie/series title
        :param int season: the series season number
        :param int episode: the series episode number
        :param int year: the movie/series year
        :return: a list of subtitles that matches the query parameters
        :rtype: `list` of :class:`~subliminal.providers.LegendasTvSubtitle`

        """
        candidates = self.search_candidates(title, season, episode, year)

        # The language code used by legendas.tv
        language_code = language.legendastv

        # Regex to extract rating information (number of downloads and rate). e.g.: 12345 downloads, nota 10
        rating_info_re = re.compile('(\d*) downloads, nota (\d{0,2})')

        # Regex to extract the last update timestamp. e.g.: 25/12/2014 - 19:25
        timestamp_info_re = re.compile('(\d{1,2}/\d{1,2}/\d{2,4} \- \d{1,2}:\d{1,2})')

        # Regex to identify the 'pack' suffix that candidates might have. e.g.: (p)Breaking.Bad.S05.HDTV.x264
        pack_name_re = re.compile('^\(p\)')

        # Regex to extract the subtitle_id from the 'href'. e.g.: /download/560014472eb4d/foo/bar
        subtitle_href_re = re.compile('/download/(\w+)/.+')

        subtitles = []
        # loop over matched movies/shows
        for candidate in candidates:
            # page_url: {server_url}/util/carrega_legendas_busca_filme/{title_id}/{language_code}
            candidate_id = candidate.get('id')
            page_url = '%s/util/carrega_legendas_busca_filme/%s/%d' % (self.server_url, candidate_id, language_code)

            # loop over paginated results
            while page_url:
                # query the server
                r = self.session.get(page_url, timeout=TIMEOUT)
                r.raise_for_status()

                soup = ParserBeautifulSoup(r.content, ['html.parser'])
                div_tags = soup.find_all('div', {'class': 'f_left'})

                # loop over each div which contains information about a single subtitle
                for div in div_tags:
                    a_tag = div.p.a
                    a_tag_text = a_tag.string if isinstance(a_tag.string, str) else a_tag.string.encode('utf-8')

                    # Removing forward-slashes from the candidate name (common practice in legendas.tv), since it
                    # misleads guessit to identify the candidate name as a file in a specific folder (which is wrong).
                    candidate_name = pack_name_re.sub('', a_tag_text).replace('/', '.')
                    page_link = a_tag['href']
                    subtitle_href_match = subtitle_href_re.search(page_link)
                    subtitle_id = subtitle_href_match.group(1) if subtitle_href_match else None
                    multiple_episodes = bool(div.find_parent('div', {'class': 'pack'}) or
                                             pack_name_re.findall(a_tag_text))
                    featured = bool(div.find_parent('div', {'class': 'destaque'}))
                    rating_info_match = rating_info_re.search(div.text)
                    no_downloads_text = rating_info_match.group(1) if rating_info_match else None
                    no_downloads = int(no_downloads_text) if no_downloads_text and no_downloads_text.isdigit() else None
                    rating_text = rating_info_match.group(2) if rating_info_match else None
                    rating = int(rating_text) if rating_text and rating_text.isdigit() else None
                    timestamp_info_match = timestamp_info_re.search(div.text)
                    timestamp = timestamp_info_match.group(1) if timestamp_info_match else None

                    # Using the candidate name to filter out bad candidates
                    # (wrong type, wrong episode, wrong season or even wrong title)
                    guess = guessit(candidate_name, {'type': candidate.get('type')})
                    if not self.matches(guess, expected_title=title, expected_season=season, expected_episode=episode,
                                        expected_year=year, ignore_episode=multiple_episodes):
                        continue

                    # Unfortunately, the only possible way to know the release names of a specific candidate is to
                    # download the compressed file (rar/zip) and list the file names.
                    handler = LegendasTvArchiveHandler(self)
                    subtitle_names = handler.get_subtitle_names(subtitle_id, timestamp)

                    if not subtitle_names:
                        continue

                    for name in subtitle_names:
                        # Filtering out bad candidates (one archive might contain subtitles for the whole season,
                        # therefore this filtering is necessary)
                        guess = guessit(os.path.splitext(name)[0], {'type': candidate.get('type')})
                        if not self.matches(guess, expected_title=title, expected_season=season,
                                            expected_episode=episode, expected_year=year):
                            continue

                        subtitle = LegendasTvSubtitle(language, page_link, subtitle_id, name, handler.binary_content,
                                                      imdb_id=candidate.get('imdb_id'), type=candidate.get('type'),
                                                      season=candidate.get('season'), year=candidate.get('year'),
                                                      no_downloads=no_downloads, rating=rating, featured=featured,
                                                      multiple_episodes=multiple_episodes, timestamp=timestamp)

                        logger.debug('Found subtitle %s', subtitle)
                        subtitles.append(subtitle)

                next_page_link = soup.find('a', attrs={'class': 'load_more'}, text='carregar mais')
                page_url = self.server_url + next_page_link['href'] if next_page_link else None

        # High quality subtitles should have higher precedence when their scores are equal.
        subtitles.sort(key=lambda s: (s.featured, s.no_downloads, s.rating, s.multiple_episodes), reverse=True)

        return subtitles

    def list_subtitles(self, video, languages):
        """
        Returns a list of subtitles for the defined video and requested languages

        :param video:
        :param languages: the requested languages
        :return: a list of subtitles for the requested video and languages
        :rtype : `list` of :class:`~subliminal.providers.LegendasTvSubtitle`

        """
        season = episode = None
        if isinstance(video, Episode):
            title = video.series
            season = video.season
            episode = video.episode
        else:
            title = video.title
        year = video.year

        return [s for l in languages for s in self.query(l, title, season=season, episode=episode, year=year)]

    def get_subtitle_names(self, content):
        """
        Returns all subtitle names for the given rar/zip binary content.

        :param content: the downloaded binary content (rar/zip)
        :return: list of subtitle names
        :rtype: `list` of `string`

        """
        cf = self.get_compressed_file(content)
        if cf:
            # open the compressed file
            with cf:
                return [f for f in cf.namelist()
                        if 'legendas.tv' not in f.lower() and f.lower().endswith(SUBTITLE_EXTENSIONS)]

    def extract_subtitle(self, content, subtitle_name):
        """
        Extract the subtitle content from the compressed file. The file is downloaded, the subtitle_name is uncompressed
        and its contents is returned.

        :param content: the downloaded binary content (rar/zip)
        :param str subtitle_name: the filename to be extracted
        :return: the subtitle content
        :rtype : `string`

        """
        cf = self.get_compressed_file(content)
        if cf:
            # open the compressed file
            with cf:
                return fix_line_ending(cf.read(subtitle_name))

    def get_compressed_file(self, content):
        bc = io.BytesIO(content)

        return RarFile(bc) if is_rarfile(bc) else (ZipFile(bc) if is_zipfile(bc) else None)

    def download_content(self, subtitle_id, timestamp):
        """
        Downloads the compressed file for the specified subtitle_id. The timestamp is required in order to avoid the
        cache when the compressed file is updated (it's a common practice in legendas.tv to update the archive with new
        subtitles)

        :param str subtitle_id: the id used to download the compressed file
        :param str timestamp: represents the last update timestamp of the file
        :return: the downloaded file
        :rtype : `bytearray`

        """
        logger.debug('Downloading subtitle_id %s. Last update on %s', subtitle_id, timestamp)
        r = self.session.get('%s/downloadarquivo/%s' % (self.server_url, subtitle_id), timeout=TIMEOUT)
        r.raise_for_status()

        return r.content

    def download_subtitle(self, subtitle):
        bc = subtitle.binary_content if subtitle.binary_content else \
            self.download_content(subtitle.subtitle_id, subtitle.timestamp)

        subtitle.content = self.extract_subtitle(bc, subtitle.name)


# Using a handler in order to be able to cache the subtitle names and keep the downloaded content
# 1st execution downloads all candidates and cache the subtitle names
# Sub-sequential executions retrieves the cached names and downloads the content only for the selected subtitle
# In a common scenario:
#   1st execution downloads 15 files
#   Sub-sequential executions download 1 file
class LegendasTvArchiveHandler:

    def __init__(self, provider, binary_content=None):
        self.provider = provider
        self.binary_content = binary_content

    @region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def get_subtitle_names(self, subtitle_id, timestamp):
        self.binary_content = self.provider.download_content(subtitle_id, timestamp)
        return self.provider.get_subtitle_names(self.binary_content)
