# -*- coding: utf-8 -*-
import json
import logging
import os
import re

from babelfish import Language, language_converters
from guessit import guess_file_info
from rarfile import RarFile, is_rarfile
from requests import Session
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, is_zipfile

from . import ParserBeautifulSoup, Provider, get_version
from .. import __version__
from ..cache import SHOW_EXPIRATION_TIME, region
from ..exceptions import AuthenticationError, ConfigurationError, ProviderError
from ..subtitle import Subtitle, fix_line_ending, guess_matches, compute_score
from ..video import Episode, Movie, SUBTITLE_EXTENSIONS

TIMEOUT = 10

logger = logging.getLogger(__name__)


class LegendasTvSubtitle(Subtitle):
    provider_name = 'legendastv'

    def __init__(self, language, page_link, subtitle_id, name, imdb_id=None, type=None, season=None, year=None,
                 no_downloads=None, rating=None, featured=False, multiple_episodes=False, guess=None, video=None):
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
        self.guess = guess  # Do not need to guess it again if it was guessed before
        self.video = video

    @property
    def id(self):
        return self.subtitle_id + ': ' + self.name

    def get_matches(self, video, hearing_impaired=False):
        matches = super(LegendasTvSubtitle, self).get_matches(video, hearing_impaired=hearing_impaired)

        # The best available information about a subtitle is its name. Using guessit to parse it.
        guess = self.guess if self.guess else guess_file_info(self.name + '.mkv', type=self.type)
        matches |= guess_matches(video, guess)

        # Only for series: It's really common to have packs which contains subtitles for the whole season
        if type == 'episode' and not guess.get('episodeNumber') and self.multiple_episodes:
            matches.add('episode')

        # imdb_id match used only for movies
        if type == 'movie' and video.imdb_id and self.imdb_id == video.imdb_id:
            matches.add('imdb_id')

        return matches


class LegendasTvProvider(Provider):
    languages = {Language.fromlegendastv(l) for l in language_converters['legendastv'].codes}
    video_types = (Episode, Movie)

    server_url = 'http://legendas.tv'

    auth_error_msg_re = re.compile(u'.*Usuário ou senha inválidos.*')
    season_re = re.compile('.*? - (\d{1,2}).*?((emporada)|(Season))', re.IGNORECASE)  # 1a Temporada | 3\u00aa Temporada
    rating_info_re = re.compile('(\d*) downloads, nota (\d{0,2})')  # 12345 downloads, nota 10
    imdb_re = re.compile('t{0,2}(\d+)')  # tt02342
    pack_name_re = re.compile('^\(p\)')  # Titles might have this suffix. E.g.: (p)Breaking.Bad.S05.HDTV.x264
    subtitle_href_re = re.compile('/download/(\w+)/.+')  # /download/560014472eb4d/sometext/othertext
    word_split_re = re.compile('(\w[\w]*)', re.IGNORECASE)

    def __init__(self, username=None, password=None):
        if username is not None and password is None or username is None and password is not None:
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.logged_in = False

    def initialize(self):
        self.session = Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % get_version(__version__)}

        # login
        if self.username is not None and self.password is not None:
            logger.info('Logging in')
            data = {'_method': 'POST', 'data[User][username]': self.username, 'data[User][password]': self.password}
            r = self.session.post('%s/login' % self.server_url, data, allow_redirects=False, timeout=TIMEOUT)
            r.raise_for_status()
            soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
            auth_error = soup.find('div', {'class': 'alert-error'}, text=self.auth_error_msg_re)

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

    def name_matches(self, expected_name, actual_name):
        words = self.word_split_re.findall(expected_name)
        name_regex_re = re.compile('(.*' + '\W+'.join(words) + '.*)', re.IGNORECASE)

        return name_regex_re.match(actual_name)

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search_titles(self, movie, series, season, year):
        """
        Returns a ``list`` that contains multiple shows or movies information by querying `/legenda/sugestao` page.
        Some results might not match the movie/series that was requested since this page is a suggestion that considers
        other fields apart from the title name.

        e.g.: /legendas/busca/2012 returns movies that contains 2012 in their description, such as "Crawlspace",
        therefore additional filtering is required to consider only the results that are matching.

        The title type (movie or series) is also considered to reject wrong suggestions.
        Additional filtering is in place: year (for movies) and season (for series)

        :param movie: guessed movie name from the input file
        :param series: guessed series name from the input file
        :param season: guessed season number from the input file
        :param year: guessed year from the input file
        :return: `list`` of ``dict`` with show or movie information :rtype: : list
        """

        keyword = movie if movie else series
        logger.info('Searching titles using the keyword %r', keyword)
        r = self.session.get('%s/legenda/sugestao/%s' % (self.server_url, keyword), timeout=TIMEOUT)
        r.raise_for_status()

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

        results = json.loads(r.text)

        mapping = dict(
            id='id_filme',
            name='dsc_nome',
            name_br='dsc_nome_br',
            year='dsc_data_lancamento',
            type='tipo',
            season='temporada',
            imdb_id='id_imdb'
        )

        typemap = {
            'M': 'movie',
            'S': 'episode',
            'C': 'episode'  # Considering C as episode. Probably C stands for Collections
        }

        candidates = []
        for result in results:
            entry = result['_source']
            item = {k: entry.get(v, None) for k, v in mapping.items()}

            # Using typemap code convention
            item['type'] = typemap.get(item.get('type'), 'movie')

            # Skipping when no id or when the item doesn't match the media type (movie or episode)
            if not item.get('id'):
                logger.debug('Rejected title due to no id: %r' % item.get('name'))
                continue

            if series and item['type'] != 'episode':
                logger.debug("Rejected title %r: Expected type 'episode' but it was '%r'" %
                             (item.get('name'), item.get('type')))
                continue

            if movie and item['type'] != 'movie':
                logger.debug("Rejected title %r: Expected type 'movie' but it was '%r'" %
                             (item.get('name'), item.get('type')))
                continue

            if not self.name_matches(keyword, item.get('name')):
                logger.debug("Rejected title %r: Title name '%r' doesnt match expected name '%r'" %
                             (item.get('id'), item.get('name'), keyword))
                continue

            item['imdb_id'] = (lambda m: m.group(1) if m else None)(self.imdb_re.search(item.get('imdb_id')))
            item['imdb_id'] = (lambda v: int(v) if v and v.isdigit() else None)(item.get('imdb_id'))
            item['year'] = (lambda v: int(v) if v and v.isdigit() else None)(item.get('year'))

            if movie:
                # Movies: years should match or an exact name match
                if year and year == item.get('year') or item.get('name').lower() == keyword.lower():
                    candidates.append(dict(item))
                else:
                    logger.debug("Rejected movie %r: It doesnt match expected year" % item)
            elif series:
                # Some entries doesn't have the season information in the correct field, but on the description field.
                if not item.get('season') and item.get('name_br'):
                    item['season'] = (lambda m: m.group(1) if m else None)(self.season_re.search(item.get('name_br')))

                item['season'] = (lambda v: int(v) if v and v.isdigit() else None)(item.get('season'))

                # Series: season numbers should match
                if season and season == item.get('season'):
                    candidates.append(dict(item))
                else:
                    logger.debug("Rejected series %r. It doesnt match expected season" % item)

        logger.debug('Titles found: %r', candidates)
        return candidates

    def query(self, language, video, movie=None, series=None, season=None, episode=None, year=None):
        """
            Returns a list of subtitles based on the input parameters.
            - 1st step is an initial lookup for the movie/show information (see ``search_titles``)
            - 2nd step is to lookup all the subtitles for all movies/shows matched previously

        :param video: the input video
        :param language: the requested language
        :param movie: the requested movie name
        :param series: the requested series name
        :param season: the requested season
        :param episode: the requested series episode
        :param year: the movie/series year
        :return: ``list`` of ``LegendasTvSubtitle`` :rtype: ``list``
        """
        titles = self.search_titles(movie, series, season, year)

        language_code = language.legendastv

        subtitles = []
        # loop over matched movies/shows
        for title in titles:
            # page_url: <server_url>/util/carrega_legendas_busca_filme/{title_id}/{language_code}
            page_url = '%s/util/carrega_legendas_busca_filme/%s/%d' % (self.server_url, title.get('id'), language_code)

            # loop over paginated results
            while page_url:
                # query the server
                r = self.session.get(page_url, timeout=TIMEOUT)
                r.raise_for_status()

                soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
                div_tags = soup.find_all('div', {'class': 'f_left'})

                # loop over each div which contains information about a single subtitle
                for div in div_tags:
                    link_tag = div.p.a

                    subtitle_name = self.pack_name_re.sub('', link_tag.string)
                    page_link = link_tag['href']
                    subtitle_id = (lambda m: m.group(1) if m else None)(self.subtitle_href_re.search(page_link))

                    multiple_episodes = bool(div.find_parent('div', {'class': 'pack'}) or
                                             self.pack_name_re.findall(link_tag.string))
                    featured = bool(div.find_parent('div', {'class': 'destaque'}))
                    no_downloads = (lambda m: m.group(1) if m else None)(self.rating_info_re.search(div.text))
                    rating = (lambda m: m.group(2) if m else None)(self.rating_info_re.search(div.text))

                    # LegendasTV does not keep the episode information apart from the name. Instead of
                    # creating a huge list of subtitles, better to parse the name and exclude the wrong episodes.
                    # Note 01: 'packs' contains all episodes and there's no episode information in the name,
                    # only season number
                    # Note 02: Some subtitles might be marked as 'pack' but they aren't. Therefore we should also
                    # consider the episode number if present.
                    guess = guess_file_info(subtitle_name + '.mkv', type=title.get('type'))
                    if title.get('type') == 'episode' and series and season and episode:
                        guessed_episode = guess.get('episodeNumber', episode if multiple_episodes else None)
                        if episode != guessed_episode:
                            logger.debug('Rejected %r - %r: Expected episode S%02dE%02d' %
                                         (subtitle_id, subtitle_name, season, episode))
                            continue

                    subtitle = LegendasTvSubtitle(language, page_link, subtitle_id, subtitle_name,
                                                  imdb_id=title.get('imdb_id'), type=title.get('type'),
                                                  season=title.get('season'), year=title.get('year'),
                                                  no_downloads=no_downloads, rating=rating, featured=featured,
                                                  multiple_episodes=multiple_episodes, guess=guess, video=video)

                    logger.debug('Found subtitle %r', subtitle)
                    subtitles.append(subtitle)

                next_page_link = soup.find('a', attrs={'class': 'load_more'}, text='carregar mais')
                page_url = self.server_url + next_page_link['href'] if next_page_link else None

        # High quality subtitles should have higher precedence when their scores are equal.
        subtitles.sort(key=lambda s: (s.featured, s.no_downloads, s.rating, s.multiple_episodes), reverse=True)

        return subtitles

    def list_subtitles(self, video, languages):
        subtitles = []
        if isinstance(video, Episode):
            for language in languages:
                subtitles.extend(self.query(language, video, series=video.series, season=video.season,
                                            episode=video.episode, year=video.year))
        elif isinstance(video, Movie):
            for language in languages:
                subtitles.extend(self.query(language, video, movie=video.title, year=video.year))

        return subtitles

    def download_subtitle(self, subtitle):
        """
        Downloads the subtitle from legendas.tv.

        Unfortunately, legendas.tv provides a rar/zip file with multiple subtitles inside and it's not possible
        to know what are the subtitles present in that file prior to download. To download all candidates prior
        scoring computation is not an option. Therefore a reference to the video has to be kept in the Subtitle
        object allowing the download method to choose the best one to extract.

        Here's an example:
            subtitle_id: '5506892f33d4d'
            name: 'The.Walking.Dead.S05E14.HDTV.x264-KILLERS-AFG-FUM-iFT-mSD-Cyphanix-BATV-TOPKEK'
        After downloading it, here's the file names inside the archive:
            Legendas.tv.url
            The.Walking.Dead.S05E14.1080i.HDTV.DD5.1.MPEG2-TOPKEK.srt
            The.Walking.Dead.S05E14.1080p.HDTV.x264-BATV.srt
            The.Walking.Dead.S05E14.1080p.WEB-DL.DD5.1.H.264-Cyphanix.srt
            The.Walking.Dead.S05E14.480p.HDTV.x264-mSD.srt
            The.Walking.Dead.S05E14.720p.HDTV.x264-KILLERS.srt
            The.Walking.Dead.S05E14.720p.WEB-DL.DD5.1.H.264-Cyphanix.srt
            The.Walking.Dead.S05E14.HDTV.x264-KILLERS.srt
            The.Walking.Dead.S05E14.HDTV.XviD-AFG.srt
            The.Walking.Dead.S05E14.HDTV.XviD-FUM.srt
            The.Walking.Dead.S05E14.HDTV.XviD-iFT.srt
        :param subtitle:
        """

        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get('%s/downloadarquivo/%s' % (self.server_url, subtitle.subtitle_id), timeout=TIMEOUT)
        r.raise_for_status()

        # Download content might be a rar file (most common) or a zip.
        # Unfortunately, rarfile module only works with files (no in-memory streams)
        tmp = NamedTemporaryFile()
        try:
            tmp.write(r.content)
            tmp.flush()

            cf = RarFile(tmp.name) if is_rarfile(tmp.name) else (ZipFile(tmp.name) if is_zipfile(tmp.name) else None)

            if cf:
                names = [f for f in cf.namelist() if 'legendas.tv' not in f.lower() and
                         (lambda ext: ext[1] if len(ext) > 1 else None)
                         (os.path.splitext(f.lower())) in SUBTITLE_EXTENSIONS]
                selected_name = self.select_best_name(names, subtitle)

                if selected_name:
                    subtitle.content = fix_line_ending(cf.read(selected_name))
        finally:
            tmp.close()

    def select_best_name(self, names, subtitle):
        if not names or len(names) == 0:
            return

        # Single name. Easy to choose
        if len(names) == 1:
            return names[0]

        if not subtitle.video:
            # Video is needed to guess the best subtitle to extract
            raise ProviderError('More than one file to extract and no video defined')

        selected_name = None
        higher_score = 0
        for name in names:
            base_name = os.path.splitext(name)[0]
            guess = guess_file_info(base_name + '.mkv', type=subtitle.type)
            score = compute_score(guess_matches(subtitle.video, guess), subtitle.video)

            if score > higher_score:
                selected_name = name
                higher_score = score

        return selected_name
