"""Based on https://github.com/realgam3/service.subtitles.bsplayer."""

from __future__ import annotations

import logging
import re
import secrets
import zlib
from time import sleep
from typing import TYPE_CHECKING, ClassVar, cast

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from defusedxml import ElementTree  # type: ignore[import-untyped]
from requests import Session

from subliminal.exceptions import AuthenticationError, NotInitializedProviderError
from subliminal.subtitle import Subtitle, fix_line_ending

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Set
    from xml.etree.ElementTree import Element

    from subliminal.video import Video

logger = logging.getLogger(__name__)

# s1-9, s101-109
SUB_DOMAINS = [
    's1',
    's2',
    's3',
    's4',
    's5',
    's6',
    's7',
    's8',
    's9',
    's101',
    's102',
    's103',
    's104',
    's105',
    's106',
    's107',
    's108',
    's109',
]
API_URL_TEMPLATE = 'http://{sub_domain}.api.bsplayer-subtitles.com/v1.php'


def get_sub_domain() -> str:
    """Get a random subdomain."""
    return API_URL_TEMPLATE.format(sub_domain=SUB_DOMAINS[secrets.randbelow(len(SUB_DOMAINS))])


def try_int(value: str | None) -> int | None:
    """Try converting value to int or None."""
    if value is None or value == '':
        return None

    try:
        return int(value)
    except ValueError:
        logger.exception('Error parsing value.')
        return None


def try_float(value: str | None) -> float | None:
    """Try converting value to float or None."""
    if value is None or value == '':
        return None

    try:
        return float(value)
    except ValueError:
        logger.exception('Error parsing value.')
        return None


def try_str(value: str | None) -> str | None:
    """Try converting value to str or None."""
    if value is None or value == '':
        return None
    return value


class BSPlayerSubtitle(Subtitle):
    """BSPlayer Subtitle."""

    provider_name: ClassVar[str] = 'bsplayer'
    series_re = re.compile(r'^"(?P<series_name>.*)" (?P<series_title>.*)$')

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        size: int | None = None,
        page_link: str | None = None,
        filename: str = '',
        subtitle_format: str | None = None,
        subtitle_hash: str | None = None,
        rating: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        encoding: str | None = None,
        imdb_id: str | None = None,
        imdb_rating: str | None = None,
        movie_year: int | None = None,
        movie_name: str | None = None,
        movie_hash: str | None = None,
        movie_size: int | None = None,
        movie_fps: float | None = None,
    ) -> None:
        super().__init__(language, subtitle_id, page_link=page_link, encoding=encoding)
        self.size = size
        self.page_link = page_link
        self.language = language
        self.filename = filename
        self.format = subtitle_format
        self.hash = subtitle_hash
        self.rating = rating
        self.season = season
        self.episode = episode
        self.encoding = encoding
        self.imdb_id = imdb_id
        self.imdb_rating = imdb_rating
        self.movie_year = movie_year
        self.movie_name = movie_name
        self.movie_hash = movie_hash
        self.movie_size = movie_size
        self.movie_fps = movie_fps

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        if not self.filename and not self.movie_name:
            return self.subtitle_id
        if self.movie_name and len(self.movie_name) > len(self.filename):
            return self.movie_name
        return self.filename

    @property
    def series_name(self) -> str | None:
        """The series name matched from `movie_name`."""
        if self.movie_name:
            matches = self.series_re.match(self.movie_name)
            if matches:
                return matches.group('series_name')
        return None

    @property
    def series_title(self) -> str | None:
        """The series title matched from `movie_name`."""
        if self.movie_name:
            matches = self.series_re.match(self.movie_name)
            if matches:
                return matches.group('series_title')
        return None

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        return {'hash'}


class BSPlayerProvider(Provider):
    """BSPlayer Provider."""

    languages: ClassVar[Set[Language]] = {Language.fromalpha3b(lang) for lang in language_converters['alpha3b'].codes}

    timeout: int
    token: str | None
    session: Session
    search_url: str

    def __init__(self, search_url: str | None = None, timeout: int = 10) -> None:
        self.timeout = timeout
        self.token = None
        self.session = Session()
        self.search_url = search_url or get_sub_domain()

    def _api_request(self, func_name: str = 'logIn', params: str = '', tries: int = 5) -> Element:
        """Request data from search url.

        :param str func_name: the type of request.
        :param str params: xml string of parameters to send with the request.
        :return: the root XML element from the response.
        :rtype: `xml.etree.ElementTree.Element`.
        """
        headers = {
            'User-Agent': 'BSPlayer/2.x (1022.12360)',
            'Content-Type': 'text/xml; charset=utf-8',
            'Connection': 'close',
            'SOAPAction': f'"http://api.bsplayer-subtitles.com/v1.php#{func_name}"',
            'Accept-Encoding': 'gzip, deflate',
        }
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{self.search_url}">'
            '<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<ns1:{func_name}>{params}</ns1:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
        )

        for _ in range(tries):
            try:
                res = self.session.post(self.search_url, data=data, headers=headers, timeout=self.timeout)
                return cast('Element', ElementTree.fromstring(res.content))
            except Exception:
                logger.exception('[BSPlayer] ERROR:.')
                if func_name == 'logIn':
                    self.search_url = get_sub_domain()
                sleep(1)
        msg = f'[BSPlayer] ERROR: Too many tries ({tries})...'
        raise AuthenticationError(msg)

    def initialize(self) -> None:
        """Initialize the provider."""
        root = self._api_request(
            func_name='logIn',
            params='<username></username><password></password><AppID>BSPlayer v2.67</AppID>',
        )
        res = root.find('.//return')
        if res is None or res.findtext('status') != 'OK':
            msg = '[BSPlayer] ERROR: Unable to login.'
            raise AuthenticationError(msg)
        self.token = try_str(res.findtext('data'))

    def terminate(self) -> None:
        """Terminate the provider."""
        if self.token is None:
            raise NotInitializedProviderError
        root = self._api_request(func_name='logOut', params=f'<handle>{self.token}</handle>')
        res = root.find('.//return')
        if res is None or res.findtext('status') != 'OK':
            msg = '[BSPlayer] ERROR: Unable to close session.'
            logger.error(msg)
        self.token = None

    def query(
        self,
        languages: Set[Language],
        file_hash: str | None = None,
        size: int | None = None,
    ) -> list[BSPlayerSubtitle]:
        """Query the provider for subtitles."""
        if self.token is None:
            raise NotInitializedProviderError
        # fill the search criteria
        language_ids = ','.join(sorted(lang.alpha3 for lang in languages))
        root = self._api_request(
            func_name='searchSubtitles',
            params=(
                f'<handle>{self.token}</handle>'
                f'<movieHash>{file_hash}</movieHash>'
                f'<movieSize>{size}</movieSize>'
                f'<languageId>{language_ids}</languageId>'
                '<imdbId>*</imdbId>'
            ),
        )
        res = root.find('.//return/result')
        if res is None or res.findtext('status') != 'OK':
            return []

        items = root.findall('.//return/data/item')
        subtitles = []
        if items:
            for item in items:
                language = Language.fromalpha3b(item.findtext('subLang'))
                subtitle = BSPlayerSubtitle(
                    language=language,
                    subtitle_id=item.findtext('subID', default=''),
                    page_link=item.findtext('subDownloadLink', default=''),
                    filename=item.findtext('subName', default=''),
                    size=try_int(item.findtext('subSize')),
                    subtitle_format=try_str(item.findtext('subFormat')),
                    subtitle_hash=try_str(item.findtext('subHash')),
                    rating=try_str(item.findtext('subRating')),
                    season=try_int(item.findtext('season')),
                    episode=try_int(item.findtext('episode')),
                    encoding=try_str(item.findtext('encsubtitle')),
                    imdb_id=try_str(item.findtext('movieIMBDID')),
                    imdb_rating=try_str(item.findtext('movieIMBDRating')),
                    movie_year=try_int(item.findtext('movieYear')),
                    movie_name=try_str(item.findtext('movieName')),
                    movie_hash=try_str(item.findtext('movieHash')),
                    movie_size=try_int(item.findtext('movieSize')),
                    movie_fps=try_float(item.findtext('movieFPS')),
                )
                logger.debug('Found subtitle %s', subtitle)
                subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[BSPlayerSubtitle]:
        """List all the subtitles for the video."""
        return self.query(languages, file_hash=video.hashes.get('bsplayer'), size=video.size)

    def download_subtitle(self, subtitle: BSPlayerSubtitle) -> None:
        """Download the content of the subtitle."""
        logger.info('Downloading subtitle %r', subtitle)
        headers = {
            'User-Agent': 'BSPlayer/2.x (1022.12360)',
            'Content-Length': '0',
        }
        r = self.session.get(subtitle.page_link or '', headers=headers, timeout=self.timeout)
        subtitle.content = fix_line_ending(zlib.decompress(r.content, 47))
