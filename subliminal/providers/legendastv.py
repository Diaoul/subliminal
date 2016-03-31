# -*- coding: utf-8 -*-
import io
import json
import logging
import os
import re

from babelfish import Language, language_converters
from dogpile.cache.api import NO_VALUE
from guessit import guessit
import rarfile
from rarfile import RarFile, is_rarfile
from requests import Session
from zipfile import ZipFile, is_zipfile

from . import ParserBeautifulSoup, Provider
from .. import __short_version__
from ..cache import EPISODE_EXPIRATION_TIME, SHOW_EXPIRATION_TIME, region
from ..exceptions import AuthenticationError, ConfigurationError
from ..subtitle import SUBTITLE_EXTENSIONS, Subtitle, fix_line_ending, guess_matches, sanitize
from ..video import Episode, Movie

logger = logging.getLogger(__name__)

language_converters.register('legendastv = subliminal.converters.legendastv:LegendasTVConverter')

# Configure :mod:`rarfile` to use the same path separator as :mod:`zipfile`
rarfile.PATH_SEP = '/'

#: Conversion map for types
type_map = {'M': 'movie', 'S': 'episode', 'C': 'episode'}

#: BR title season parsing regex
season_re = re.compile(' - (?P<season>\d+)(\xaa|a) temporada', re.IGNORECASE)

#: Rating parsing regex
rating_re = re.compile('^(?P<downloads>\d+) downloads, nota (?P<rating>\d+)?')

#: Cache key for releases
releases_key = __name__ + ':releases|{archive_id}'


class LegendasTVArchive(object):
    """LegendasTV Archive.

    :param str id: identifier.
    :param str name: name.
    :param bool pack: contains subtitles for multiple episodes.
    :param bool pack: featured.
    :param str link: link.
    :param int downloads: download count.
    :param int rating: rating (0-10).

    """
    def __init__(self, id, name, pack, featured, link, downloads=None, rating=None):
        #: Identifier
        self.id = id

        #: Name
        self.name = name

        #: Pack
        self.pack = pack

        #: Featured
        self.featured = featured

        #: Link
        self.link = link

        #: Download count
        self.downloads = downloads

        #: Rating  (0-10)
        self.rating = rating

        #: Compressed content as :class:`rarfile.RarFile` or :class:`zipfile.ZipFile`
        self.content = None

    def __repr__(self):
        return '<%s [%s] %r>' % (self.__class__.__name__, self.id, self.name)


class LegendasTVSubtitle(Subtitle):
    """LegendasTV Subtitle."""
    provider_name = 'legendastv'

    def __init__(self, language, type, title, year, imdb_id, season, archive, name):
        super(LegendasTVSubtitle, self).__init__(language, archive.link)
        self.type = type
        self.title = title
        self.year = year
        self.imdb_id = imdb_id
        self.season = season
        self.archive = archive
        self.name = name

    @property
    def id(self):
        return '%s-%s' % (self.archive.id, self.name.lower())

    def get_matches(self, video, hearing_impaired=False):
        matches = set()

        # episode
        if isinstance(video, Episode) and self.type == 'episode':
            # series
            if video.series and sanitize(self.title) == sanitize(video.series):
                matches.add('series')

            # year (year is based on season air date hence the adjustment)
            if video.original_series and self.year is None or video.year and video.year == self.year - self.season + 1:
                matches.add('year')

            # imdb_id
            if video.series_imdb_id and self.imdb_id == video.series_imdb_id:
                matches.add('series_imdb_id')

        # movie
        elif isinstance(video, Movie) and self.type == 'movie':
            # title
            if video.title and sanitize(self.title) == sanitize(video.title):
                matches.add('title')

            # year
            if video.year and self.year == video.year:
                matches.add('year')

            # imdb_id
            if video.imdb_id and self.imdb_id == video.imdb_id:
                matches.add('imdb_id')

        # archive name
        matches |= guess_matches(video, guessit(self.archive.name, {'type': self.type}))

        # name
        matches |= guess_matches(video, guessit(self.name, {'type': self.type}))

        return matches


class LegendasTVProvider(Provider):
    """LegendasTV Provider.

    :param str username: username.
    :param str password: password.

    """
    languages = {Language.fromlegendastv(l) for l in language_converters['legendastv'].codes}
    server_url = 'http://legendas.tv/'

    def __init__(self, username=None, password=None):
        if username and not password or not username and password:
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
            r = self.session.post(self.server_url + 'login', data, allow_redirects=False, timeout=10)
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
            r = self.session.get(self.server_url + 'users/logout', allow_redirects=False, timeout=10)
            r.raise_for_status()
            logger.debug('Logged out')
            self.logged_in = False

        self.session.close()

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search_titles(self, title):
        """Search for titles matching the `title`.

        :param str title: the title to search for.
        :return: found titles.
        :rtype: dict

        """
        # make the query
        logger.info('Searching title %r', title)
        r = self.session.get(self.server_url + 'legenda/sugestao/{}'.format(title), timeout=10)
        r.raise_for_status()
        results = json.loads(r.text)

        # loop over results
        titles = {}
        for result in results:
            source = result['_source']

            # extract id
            title_id = int(source['id_filme'])

            # extract type, title and year
            title = {'type': type_map[source['tipo']], 'title': source['dsc_nome'],
                     'year': int(source['dsc_data_lancamento'])}

            # extract imdb_id
            if source['id_imdb'] != '0':
                if not source['id_imdb'].startswith('tt'):
                    title['imdb_id'] = 'tt' + source['id_imdb'].zfill(7)
                else:
                    title['imdb_id'] = source['id_imdb']

            # extract season
            if title['type'] == 'episode':
                if source['temporada'] is not None:
                    title['season'] = int(source['temporada'])
                else:
                    match = season_re.search(source['dsc_nome_br'])
                    title['season'] = int(match.group('season'))

            # add title
            titles[title_id] = title

        logger.debug('Found %d titles', len(titles))

        return titles

    @region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def get_archives(self, title_id, language_code):
        """Get the archive list from a given `title_id` and `language_code`.

        :param int title_id: title id.
        :param int language_code: language code.
        :return: the archives.
        :rtype: list of :class:`LegendasTVArchive`

        """
        logger.info('Getting archives for title %d and language %d', title_id, language_code)
        archives = []
        page = 1
        while True:
            # get the archive page
            url = self.server_url + 'util/carrega_legendas_busca_filme/{title}/{language}/-/{page}'.format(
                title=title_id, language=language_code, page=page)
            r = self.session.get(url)
            r.raise_for_status()

            # parse the results
            soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
            for archive_soup in soup.select('div.list_element > article > div'):
                # create archive
                archive = LegendasTVArchive(archive_soup.a['href'].split('/')[2], archive_soup.a.text,
                                            'pack' in archive_soup['class'], 'destaque' in archive_soup['class'],
                                            self.server_url + archive_soup.a['href'][1:])

                # match rating
                match = rating_re.match(archive_soup.find('p', class_='data').text)
                archive.downloads = int(match.group('downloads'))
                if match.group('rating') is not None:
                    archive.rating = int(match.group('rating'))

                # add archive
                archives.append(archive)

            # stop on last page
            if soup.find('a', attrs={'class': 'load_more'}, text='carregar mais') is None:
                break

            # increment page count
            page += 1

        logger.debug('Found %d archives', len(archives))

        return archives

    def download_archive(self, archive):
        """Download an archive's :attr:`~LegendasTVArchive.content`.

        :param archive: the archive to download :attr:`~LegendasTVArchive.content` of.
        :type archive: :class:`LegendasTVArchive`

        """
        logger.info('Downloading archive %s', archive.id)
        r = self.session.get(self.server_url + 'downloadarquivo/{}'.format(archive.id))
        r.raise_for_status()

        # open the archive
        archive_stream = io.BytesIO(r.content)
        if is_rarfile(archive_stream):
            logger.debug('Identified rar archive')
            archive.content = RarFile(archive_stream)
        elif is_zipfile(archive_stream):
            logger.debug('Identified zip archive')
            archive.content = ZipFile(archive_stream)
        else:
            raise ValueError('Not a valid archive')

    def query(self, language, title, season=None, episode=None, year=None):
        # search for titles
        titles = self.search_titles(sanitize(title))

        # search for titles with the quote character
        if '\'' in title:
            titles.update(self.search_titles(sanitize(title, ignore_characters={'\''})))

        subtitles = []
        # iterate over titles
        for title_id, t in titles.items():
            # discard mismatches on title
            if sanitize(t['title']) != sanitize(title):
                continue

            # episode
            if season and episode:
                # discard mismatches on type
                if t['type'] != 'episode':
                    continue

                # discard mismatches on season
                if t['season'] != season:
                    continue
            # movie
            else:
                # discard mismatches on type
                if t['type'] != 'movie':
                    continue

                # discard mismatches on year
                if year is not None and t['year'] != year:
                    continue

            # iterate over title's archives
            for a in self.get_archives(title_id, language.legendastv):
                # clean name of path separators and pack flags
                clean_name = a.name.replace('/', '-')
                if a.pack and clean_name.startswith('(p)'):
                    clean_name = clean_name[3:]

                # guess from name
                guess = guessit(clean_name, {'type': t['type']})

                # episode
                if season and episode:
                    # discard mismatches on episode in non-pack archives
                    if not a.pack and 'episode' in guess and guess['episode'] != episode:
                        continue

                # attempt to get the releases from the cache
                releases = region.get(releases_key.format(archive_id=a.id))

                # the releases are not in cache or cache is expired
                if releases == NO_VALUE:
                    logger.info('Releases not found in cache')

                    # download archive
                    self.download_archive(a)

                    # extract the releases
                    releases = []
                    for name in a.content.namelist():
                        # discard the legendastv file
                        if name.startswith('Legendas.tv'):
                            continue

                        # discard hidden files
                        if os.path.split(name)[-1].startswith('.'):
                            continue

                        # discard non-subtitle files
                        if not name.lower().endswith(SUBTITLE_EXTENSIONS):
                            continue

                        releases.append(name)

                    # cache the releases
                    region.set(releases_key.format(archive_id=a.id), releases)

                # iterate over releases
                for r in releases:
                    subtitle = LegendasTVSubtitle(language, t['type'], t['title'], t['year'], t.get('imdb_id'),
                                                  t.get('season'), a, r)
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        season = episode = None
        if isinstance(video, Episode):
            title = video.series
            season = video.season
            episode = video.episode
        else:
            title = video.title

        return [s for l in languages for s in self.query(l, title, season=season, episode=episode, year=video.year)]

    def download_subtitle(self, subtitle):
        # download archive in case we previously hit the releases cache and didn't download it
        if subtitle.archive.content is None:
            self.download_archive(subtitle.archive)

        # extract subtitle's content
        subtitle.content = fix_line_ending(subtitle.archive.content.read(subtitle.name))
