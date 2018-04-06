# -*- coding: utf-8 -*-
import logging

from babelfish import Language
from guessit import guessit
import requests
import zipfile
import io
import os

from . import Provider
from .. import __short_version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..video import Episode, Movie

logger = logging.getLogger(__name__)

_SERVER_API_URL = "http://api.wizdom.xyz/"
_SERVER_ZIP_URL = "http://zip.wizdom.xyz/"


class WizdomSubtitle(Subtitle):
    """WizDom subtitle."""

    provider_name = "wizdom"

    def __init__(self, imdb_id, api_dict):
        super(WizdomSubtitle, self).__init__(Language('heb'))

        print("Wizdom subtitle created")

        self._imdb_id = imdb_id
        self._api_dict = api_dict

    @property
    def id(self):

        return self._api_dict['id']

    @property
    def download_url(self):

        return "{0}{1}.zip".format(_SERVER_ZIP_URL, self._api_dict['id'])

    def get_matches(self, video):

        matches = set()

        if isinstance(video, Episode):
            matches |= guess_matches(video, guessit(
                self._api_dict['versioname'], {'type': 'episode'}))
        elif isinstance(video, Movie):
            matches |= guess_matches(video, guessit(
                self._api_dict['versioname'], {'type': 'movie'}))
        else:
            logger.info("Got video of unexpected type")

        if video.imdb_id and self._imdb_id == video.imdb_id:
            matches.add("imdb_id")

        return matches


class WizdomProvider(Provider):

    languages = {Language(l) for l in ['heb']}

    def __init__(self):

        self._session = None

    def initialize(self):

        self._session = requests.Session()
        self._session.headers[
            'User-Agent'] = 'Subliminal/{}'.format(__short_version__)

    def terminate(self):

        self._session.close()

    def query(self, file_name, imdb_id, season=None, episode=None):

        logger.info('Searching subtitles %s', file_name)

        if season is None:
            season = 0
        if episode is None:
            episode = 0

        response = self._session.get(_SERVER_API_URL + "search.id.php",
                                     params={"imdb": imdb_id, "season": season, "episode": episode, "version": file_name})
        response.raise_for_status()

        if response.text == "":
            return []

        return [WizdomSubtitle(imdb_id, d) for d in response.json()]

    def list_subtitles(self, video, languages):

        season = episode = None
        imdb_id = video.imdb_id
        if isinstance(video, Episode):
            season = video.season
            episode = video.episode
            imdb_id = video.series_imdb_id

        return self.query(os.path.basename(video.name), imdb_id, season, episode)

    def download_subtitle(self, subtitle):

        logger.info('Downloading subtitle %r', subtitle)

        response = self._sesson.get(subtitle.download_url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as f:
            for filename in f.namelist():
                root, ext = os.path.splitext(filename)

                if ext in [".srt", ".sub"]:
                    subtitle.content = fix_line_ending(f.read(filename))
                    return

        raise BadSubtitleZipFileError()


class BadSubtitleZipFileError(ProviderError):
    pass
