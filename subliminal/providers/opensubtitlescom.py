# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
import logging
import time

from babelfish import Language, language_converters
from guessit import guessit
from requests import Session
from requests_cache import CachedSession

from . import Provider
from .. import __short_version__
from ..exceptions import (
    AuthenticationError,
    ConfigurationError,
    DownloadLimitExceeded,
    ProviderError,
    ServiceUnavailable,
)
from ..matches import guess_matches
from ..subtitle import Subtitle, fix_line_ending
from ..video import Episode, Movie

logger = logging.getLogger(__name__)

language_converters.register('opensubtitlescom = subliminal.converters.opensubtitlescom:OpenSubtitlesComConverter')

#: Opensubtitles.com API key for subliminal
OPENSUBTITLESCOM_API_KEY = "mij33pjc3kOlup1qOKxnWWxvle2kFbMH"

#: Expiration time for token
DEFAULT_EXPIRATION_TIME = timedelta(days=1).total_seconds()

#: Expiration time for token
TOKEN_EXPIRATION_TIME = timedelta(hours=24).total_seconds()

#: Expiration time for download link
DOWNLOAD_EXPIRATION_TIME = timedelta(hours=3).total_seconds()

expire_after = DEFAULT_EXPIRATION_TIME
urls_expire_after = {
    'https://api.opensubtitles.com/api/v1/login': TOKEN_EXPIRATION_TIME,
    'https://api.opensubtitles.com/api/v1/download': DOWNLOAD_EXPIRATION_TIME,
}


class OpenSubtitlesComSubtitle(Subtitle):
    """OpenSubtitles.com Subtitle."""
    provider_name = 'opensubtitlescom'

    def __init__(
        self,
        language,
        hearing_impaired,
        *,
        subtitle_id = None,
        movie_kind = None,
        movie_hash = None,
        download_count = None,
        fps = None,
        from_trusted = None,
        uploader_rank = None,
        foreign_parts_only = None,
        machine_translated = None,
        release = None,
        movie_title = None,
        movie_full_name = None,
        movie_year = None,
        movie_imdb_id = None,
        movie_tmdb_id = None,
        series_season = None,
        series_episode = None,
        series_title = None,
        series_imdb_id = None,
        series_tmdb_id = None,
        file_id = None,
        file_name = None,
    ):
        super(OpenSubtitlesComSubtitle, self).__init__(
            language,
            hearing_impaired=hearing_impaired,
            page_link="",
            encoding="utf-8",
        )
        self.subtitle_id = subtitle_id
        self.movie_kind = movie_kind
        self.movie_hash = movie_hash
        self.download_count = download_count
        self.fps = fps
        self.from_trusted = from_trusted
        self.uploader_rank = uploader_rank
        self.foreign_parts_only = foreign_parts_only
        self.machine_translated = machine_translated
        self.release = release
        self.movie_title = movie_title
        self.movie_full_name = movie_full_name
        self.movie_year = movie_year
        self.movie_imdb_id = movie_imdb_id
        self.movie_tmdb_id = movie_tmdb_id
        self.series_season = series_season
        self.series_episode = series_episode
        self.series_title = series_title
        self.series_imdb_id = series_imdb_id
        self.series_tmdb_id = series_tmdb_id
        self.file_id = file_id
        self.file_name = file_name

    @property
    def id(self):
        return str(self.subtitle_id)

    @property
    def info(self):
        if not self.file_name and not self.release:
            return self.subtitle_id
        if self.release and len(self.release) > len(self.file_name):
            return self.release
        return self.file_name

    def get_matches(self, video):
        if (isinstance(video, Episode) and self.movie_kind != 'episode') or (
                isinstance(video, Movie) and self.movie_kind != 'movie'):
            logger.info('%r is not a valid movie_kind', self.movie_kind)
            return set()

        matches = guess_matches(video, {
            'title': self.series_title if self.movie_kind == 'episode' else self.movie_title,
            'episode_title': self.movie_title if self.movie_kind == 'episode' else None,
            'year': self.movie_year,
            'season': self.series_season,
            'episode': self.series_episode
        })

        # tag
        if not video.imdb_id or self.movie_imdb_id == video.imdb_id:
            if self.movie_kind == 'episode':
                matches |= {'series', 'year', 'season', 'episode'}
            elif self.movie_kind == 'movie':
                matches |= {'title', 'year'}

        # guess
        matches |= guess_matches(video, guessit(self.release, {'type': self.movie_kind}))
        matches |= guess_matches(video, guessit(self.file_name, {'type': self.movie_kind}))

        # imdb_id
        if video.imdb_id and self.movie_imdb_id == video.imdb_id:
            matches.add('imdb_id')

        return matches


class OpenSubtitlesComProvider(Provider):
    """OpenSubtitles.com Provider.

    :param str username: username.
    :param str password: password.

    """
    server_url = 'https://api.opensubtitles.com/api/v1/'
    subtitle_class = OpenSubtitlesComSubtitle
    user_agent = 'Subliminal v%s' % __short_version__
    sub_format = "srt"

    def __init__(self, username=None, password=None, *, apikey=None, cached=True):
        if any((username, password)) and not all((username, password)):
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.logged_in = False
        self.session = None
        self.token = None
        self.token_expires_at = None
        self.cached = cached
        self.apikey = apikey or OPENSUBTITLESCOM_API_KEY

    def initialize(self):
        if self.cached:
            self.session = CachedSession(
                cache_name=self.__class__.__name__,
                expire_after=expire_after,
                urls_expire_after=urls_expire_after,
            )
        else:
            self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Api-Key'] = self.apikey
        self.session.headers['Accept'] = "*/*"
        self.session.headers['Content-Type'] = "application/json"
        if self.check_token():
            self.session.headers['Authorization'] = 'Bearer ' + str(self.token)

        # login
        # self.login()

    def terminate(self):
        if not self.session:
            return

        # logout
        self.logout()

        self.session.close()

    def check_token(self):
        if not self.token:
            return False
        if self.token_expires_at and datetime.now(timezone.utc) > self.token_expires_at:
            self.token = None
            self.token_expires_at = None
            return False
        return True

    def login(self, *, wait=False):
        if not self.username or not self.password:
            logger.info('Cannot log in, a username and password must be provided')
            return

        if not self.session:
            return

        if wait:
            # Wait 1s between calls
            time.sleep(1)

        logger.info('Logging in')
        data = {'username': self.username, 'password': self.password}

        try:
            r = self.session.post(self.server_url + 'login', json=data)
            r = checked(r)
        except ProviderError:
            # raise error
            logger.exception("An error occurred")
            raise

        ret = r.json()
        self.token = ret["token"]
        if self.token:
            self.session.headers['Authorization'] = 'Bearer ' + str(self.token)
            self.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        logger.debug('Logged in')

    def logout(self):
        if not self.session:
            return
        if not self.check_token():
            return

        logger.info('Logging out')
        try:
            r = self.session.delete(self.server_url + 'logout', timeout=10)
            r = checked(r)
        except ProviderError:
            logger.exception("An error occurred")
        logger.debug('Logged out')
        self.token_expires_at = None
        self.token = None

    def try_login(self):
        if not self.check_token():
            # token expired
            self.login()

            if not self.check_token():
                logger.info("Cannot authenticate with username and password")
                return False
        return True

    def user_infos(self):
        if not self.session:
            return

        logger.debug('User infos')

        if not self.try_login():
            return {}
        response = self.api_get('infos/user')
        logger.debug(response)
        return response

    def api_post(self, path, body=None):
        body = dict(body) if body else {}

        if not self.session:
            return {}

        # no need to set the headers, there are set for `self.session`
        try:
            r = self.session.post(self.server_url + path, json=body)
            r = checked(r)
        except ProviderError:
            logger.exception("An error occurred")
            return {}

        return r.json()

    def api_get(self, path, params=None):
        # sort dict
        params = dict(sorted(params.items())) if params else {}
        # lowercase, do not transform spaces to "+", because then they become html-encoded
        params = {k.lower(): (v.lower() if isinstance(v, str) else v) for k, v in params.items()}

        if not self.session:
            return {}

        # no need to set the headers, there are set for `self.session`
        try:
            r = self.session.get(self.server_url + path, params=params)
            r = checked(r)
        except ProviderError:
            logger.exception("An error occurred")
            return {}

        return r.json()

    def _make_query(
        self,
        hash=None,
        imdb_id=None,
        tmdb_id=None,
        query=None,
        season=None,
        episode=None,
        opensubtitles_id=None,
        show_imdb_id=None,
        show_tmdb_id=None,
        year=None,
    ):
        # fill the search criterion
        criterion = {}
        if hash:
            criterion.update({'moviehash': hash})

        if imdb_id:
            criterion.update({'imdb_id': imdb_id[2:].lstrip("0")})
            if show_imdb_id:
                criterion.update({'parent_imdb_id': show_imdb_id[2:].lstrip("0")})

        if tmdb_id:
            criterion.update({'tmdb_id': str(tmdb_id).lstrip("0")})
            if show_tmdb_id:
                criterion.update({'parent_tmdb_id': str(show_tmdb_id).lstrip("0")})

        if opensubtitles_id:
            criterion.update({'id': opensubtitles_id})

        if query:
            criterion.update({'query': query.replace("'", '')})

        if season and episode:
            criterion.update({'season_number': season, 'episode_number': episode})
        if year:
            criterion.update({"year": year})

        # return a list of criteria
        if not criterion:
            return []

        criteria = [criterion]
        if "id" in criterion:
            criteria.append({"id": criterion["id"]})
        if "imdb_id" in criterion:
            criteria.append({"imdb_id": criterion["imdb_id"]})
        if "tmdb_id" in criterion:
            criteria.append({"tmdb_id": criterion["tmdb_id"]})
        if "moviehash" in criterion:
            criteria.append({"moviehash": criterion["moviehash"]})
        if "query" in criterion:
            if "season_number" in criterion and "episode_number" in criterion:
                criteria.append({
                    "query": criterion["query"],
                    "season_number": criterion["season_number"],
                    "episode_number": criterion["episode_number"],
                })
            else:
                criteria.append({"query": criterion["query"]})

        return criteria

    def _parse_single_response(self, subtitle_item):
        # read the item
        attributes = subtitle_item.get("attributes", {})
        feature_details = attributes.get("feature_details", {})

        opensubtitles_id = int(subtitle_item.get("id"))
        language = Language.fromopensubtitlescom(str(attributes.get('language')))
        download_count = int(attributes.get('download_count'))
        fps = float(attributes.get('fps'))
        hearing_impaired = bool(int(attributes.get('hearing_impaired')))
        from_trusted = bool(int(attributes.get('from_trusted')))
        uploader_rank = str(attributes.get('uploader', {}).get("rank"))
        foreign_parts_only = bool(int(attributes.get('foreign_parts_only')))
        machine_translated = bool(int(attributes.get('machine_translated')))
        release = str(attributes.get('release'))
        # subtitle_id = attributes.get('subtitle_id')


        year = int(feature_details.get('year')) if feature_details.get('year') else None
        movie_title = str(feature_details.get('title'))
        movie_kind = str(feature_details.get('feature_type').lower())
        movie_full_name = str(feature_details.get('movie_name'))
        imdb_id = 'tt' + str(feature_details.get('imdb_id')).rjust(7, "0")
        tmdb_id = feature_details.get('tmdb_id')
        season_number = int(feature_details.get('season_number')) if feature_details.get('season_number') else None
        episode_number = int(feature_details.get('episode_number')) if feature_details.get('episode_number') else None
        parent_title = str(feature_details.get('parent_title'))
        parent_imdb_id = 'tt' + str(feature_details.get('parent_imdb_id')).rjust(7, "0")
        parent_tmdb_id = feature_details.get('parent_tmdb_id')

        files = attributes.get("files", [])
        if len(files) == 0:
            srt_file = {"file_id": 0, "file_name": ""}
        else:
            srt_file = files[0]
        file_id = int(srt_file.get("file_id"))
        file_name = str(srt_file.get("file_name"))


        return self.subtitle_class(
            language,
            hearing_impaired,
            subtitle_id=opensubtitles_id,
            movie_kind=movie_kind,
            download_count=download_count,
            fps=fps,
            from_trusted=from_trusted,
            uploader_rank=uploader_rank,
            foreign_parts_only=foreign_parts_only,
            machine_translated=machine_translated,
            release=release,
            movie_title=movie_title,
            movie_full_name=movie_full_name,
            movie_year=year,
            movie_imdb_id=imdb_id,
            movie_tmdb_id=tmdb_id,
            series_season=season_number,
            series_episode=episode_number,
            series_title=parent_title,
            series_imdb_id=parent_imdb_id,
            series_tmdb_id=parent_tmdb_id,
            file_id=file_id,
            file_name=file_name,
        )

    def query(
        self,
        languages,
        hash=None,
        imdb_id=None,
        tmdb_id=None,
        query=None,
        season=None,
        episode=None,
        opensubtitles_id=None,
        show_imdb_id=None,
        show_tmdb_id=None,
        year=None,
        page=None,
    ):
        # fill the search criteria
        criteria = self._make_query(
            hash,
            imdb_id,
            tmdb_id,
            query,
            season,
            episode,
            opensubtitles_id,
            show_imdb_id,
            show_tmdb_id,
            year,
        )

        if not criteria:
            raise ValueError('Not enough information')

        subtitles = []

        for criterion in criteria:
            # add the language and query the server
            criterion.update({'languages': ','.join(sorted(l.opensubtitlescom for l in languages))})
            if page is not None:
                criterion.update({"page": page})

            # query the server
            logger.info('Searching subtitles %r', criterion)
            response = self.api_get("subtitles", criterion)

            if not response or not response['data']:
                continue

            # loop over subtitle items
            for subtitle_item in response['data']:
                # read single response
                subtitle = self._parse_single_response(subtitle_item)
                logger.debug('Found subtitle %r', subtitle)
                subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        season = episode = None
        if isinstance(video, Episode):
            # TODO: add show_imdb_id and show_tmdb_id
            query = video.series
            season = video.season
            episode = video.episode
        else:
            query = video.title

        return self.query(
            languages,
            hash=video.hashes.get('opensubtitles'),
            imdb_id=video.imdb_id,
            query=query,
            season=season,
            episode=episode,
        )

    def download_subtitle(self, subtitle):
        if not self.session:
            return
        if not self.try_login():
            return

        # get the subtitle download link
        logger.info('Downloading subtitle %r', subtitle)
        body = {"file_id": subtitle.file_id, "file_name": subtitle.file_name, "sub_format": self.sub_format}
        r = self.api_post("download", body)

        link = r["link"]
        remaining = int(r["remaining"])
        reset_time_utc = r["reset_time_utc"]

        # detect download limit exceeded
        if remaining <= 0:
            logger.error("download quota exceeded, quota reset on %s UTC", reset_time_utc)
            raise DownloadLimitReached

        # download the subtitle
        download_response = self.session.get(link)

        if not download_response.content:
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('Unable to download subtitle. No data returned from provider')
            return

        subtitle.content = fix_line_ending(download_response.content)


class OpenSubtitlesComVipSubtitle(OpenSubtitlesComSubtitle):
    """OpenSubtitles.com VIP Subtitle."""
    provider_name = 'opensubtitlescomvip'


class OpenSubtitlesComVipProvider(OpenSubtitlesComProvider):
    """OpenSubtitles.com VIP Provider."""
    server_url = 'https://vip-api.opensubtitles.com/api/v1/'
    subtitle_class = OpenSubtitlesComVipSubtitle


class OpenSubtitlesComError(ProviderError):
    """Base class for non-generic :class:`OpenSubtitlesComProvider` exceptions."""
    pass


class Unauthorized(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '401 Unauthorized'."""
    pass


class NoSession(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '406 No session'."""
    pass


class DownloadLimitReached(OpenSubtitlesComError, DownloadLimitExceeded):
    """Exception raised when status is '407 Download limit reached'."""
    pass


class InvalidImdbid(OpenSubtitlesComError):
    """Exception raised when status is '413 Invalid ImdbID'."""
    pass


class UnknownUserAgent(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '414 Unknown User Agent'."""
    pass


class DisabledUserAgent(OpenSubtitlesComError, AuthenticationError):
    """Exception raised when status is '415 Disabled user agent'."""
    pass


def checked(response):
    """Check a response status before returning it.

    :param response: a response from `requests` call to OpenSubtitlesCom.
    :return: the response.
    :raise: :class:`OpenSubtitlesComError`

    """
    status_code = response.status_code
    if status_code == 401:
        raise Unauthorized(response.reason)
    if status_code == 406:
        raise NoSession
    if status_code == 407:
        raise DownloadLimitReached
    if status_code == 413:
        raise InvalidImdbid
    if status_code == 414:
        raise UnknownUserAgent
    if status_code == 415:
        raise DisabledUserAgent
    if status_code == 503:
        raise ServiceUnavailable
    if status_code != 200:
        raise OpenSubtitlesComError(response.reason)

    return response
