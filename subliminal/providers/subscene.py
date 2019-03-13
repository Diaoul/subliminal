# -*- coding: utf-8 -*-
from io import BytesIO
from logging import getLogger
from zipfile import ZipFile

from requests import Session
from babelfish import Language, language_converters
from guessit import guessit

from . import ParserBeautifulSoup, Provider
from .. import __short_version__
from ..subtitle import Subtitle, fix_line_ending
from ..video import Episode, Movie
from ..utils import sanitize
from ..converters.subscene import supported_languages

logger = getLogger(__name__)

language_converters.register("subscene = subliminal.converters"
                             ".subscene:SubsceneConverter")

language_ids = {
    "ara":  2, "dan": 10, "nld": 11, "eng": 13, "fas": 46, "fin": 17,
    "fra": 18, "heb": 22, "ind": 44, "ita": 26, "msa": 50, "nor": 30,
    "ron": 33, "spa": 38, "swe": 39, "vie": 45, "sqi":  1, "hye": 73,
    "aze": 55, "eus": 74, "bel": 68, "ben": 54, "bos": 60, "bul":  5,
    "mya": 61, "cat": 49, "hrv":  8, "ces":  9, "epo": 47, "est": 16,
    "kat": 62, "deu": 19, "ell": 21, "kal": 57, "hin": 51, "hun": 23,
    "isl": 25, "jpn": 27, "kor": 28, "kur": 52, "lav": 29, "lit": 43,
    "mkd": 48, "mal": 64, "mni": 65, "mon": 72, "pus": 67, "pol": 31,
    "por": 32, "pan": 66, "rus": 34, "srp": 35, "sin": 58, "slk": 36,
    "slv": 37, "som": 70, "tgl": 53, "tam": 59, "tel": 63, "tha": 40,
    "tur": 41, "ukr": 56, "urd": 42, "yor": 71
}


to_ordinal = {
    0: "Zeroth", 1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth",
    6: "Sixth", 7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth",
    11: "Eleventh", 12: "Twelfth", 13: "Thirteenth", 14: "Fourteenth",
    15: "Fifteenth", 16: "Sixteenth", 17: "Seventeenth", 18: "Eighteenth",
    19: "Nineteenth", 20: "Twentieth"
}


def soupify(html):
    return ParserBeautifulSoup(html, ["html.parser"])


class SubsceneSubtitle(Subtitle):
    """Subscene Subtitle."""
    provider_name = "subscene"

    def __init__(self, language, hearing_impaired=False, page_link=None,
                 encoding=None, desc=None, zip_link=None, release_name=None,
                 release_type=None, imdb_id=None, num_files=None, year=None):
        super(SubsceneSubtitle, self).__init__(language, hearing_impaired,
                                               page_link, encoding)

        self.desc = desc
        self.zip_link = zip_link
        self.release_name = release_name
        self.release_type = release_type
        self.imdb_id = imdb_id
        self.num_files = num_files
        self.year = year

        self._desc_guess = {} if self.desc is None else guessit(self.desc)

    @property
    def id(self):
        link = self.page_link
        if link:
            assert link.startswith("/subtitles/")
            return link[11:]

    @property
    def info(self):
        return self.desc
    def get_matches(self, video):
        matches = set()

        if self.desc:
            if video.name:
                name = (self.desc, self.release_name)
                if video.name in name or self.desc in video.name:
                    matches.add("name")

            self._check_guess(video, matches, "release_group")
            self._check_guess(video, matches, "video_codec")
            self._check_guess(video, matches, "audio_codec")
            self._check_guess(video, matches, "source")
            if self.release_type and self.release_type == video.source:
                matches.add("source")

            self._check_guess(video, matches, "year")
            self._check_guess(video, matches, "title")
            self._check_guess(video, matches, "screen_size", "resolution")

        kind = self._desc_guess.get("type")
        if isinstance(video, Movie) and kind != "episode":
            if self.release_name and video.title and \
                    sanitize(self.release_name) == sanitize(video.title):
                matches.add("title")
        elif isinstance(video, Episode) and kind != "movie":
            if self.desc:
                self._check_guess(video, matches, "title", "series")
                self._check_guess(video, matches, "season")
                self._check_guess(video, matches, "episode")
                self._check_guess(video, matches, "episode_title", "title")
        else:
            logger.info("video kind mismatch (guessed: '%r')", kind)

        if self.imdb_id and self.imdb_id == video.imdb_id:
            matches.add("imdb_id")

        if self.year and self.year == video.year:
            matches.add("year")

        return matches

    def _check_guess(self, video, matches, self_prop, video_prop=None):
        if video_prop is None:
            video_prop = self_prop
        mine = self._desc_guess.get(self_prop)
        if mine:
            her = getattr(video, video_prop)
            if (isinstance(mine, str) and sanitize(mine) ==
                    sanitize(her)) or mine == her:
                matches.add(video_prop)


class SubsceneProvider(Provider):
    """Subscene Provider."""

    languages = supported_languages

    def __init__(self, hostname="subscene.com", force_ssl=False, agent=None):
        protocol = "https" if force_ssl else "http"
        self._baseurl = "%s://%s" % (protocol, hostname)
        self._agent = agent if agent else "Subliminal/%s" % __short_version__
        self._session = None
        self._filter = (set(), None)

    def initialize(self):
        if self._session is None:
            logger.info("Creating session")
            self._session = Session()
            self._session.headers["User-Agent"] = self._agent

            # apply redirections if any
            url = self._baseurl
            while True:
                with self._session.head(url, allow_redirects=False) as resp:
                    if not resp.is_redirect:
                        if resp.ok:
                            break
                        resp.raise_for_status()
                    url = resp.headers['location']
            self._baseurl = url[:-1] if url.endswith("/") else url

    def terminate(self):
        if self._session is not None:
            logger.info("Closing session")
            self._session.close()
            self._session = None

    def query(self, query, year=None, langs=None):
        # can SSF (server-side filtering) be used?
        langs = set() if langs is None else langs
        manual_filter = len(langs) > 3
        if not manual_filter:
            self._update_filter(langs)

        url = "%s/subtitles/title" % self._baseurl
        params = {"q": query, "l": ""}
        with self._session.get(url, params=params) as response:
            response.raise_for_status()
            html = response.text
        results = soupify(html).find("div", class_="search-result")
        del params, response, html

        url, li = None, None
        for kind in ("exact", "close", "popular"):
            h2 = results.find("h2", class_=kind)
            if h2 is None:
                continue

            ul = h2.next_sibling
            while ul.name != "ul":
                ul = ul.next_sibling

            for li in ul.children:
                if li.name != "li":
                    continue
                if year is not None:
                    s = li.a.string.strip()
                    y = int(s[s.rindex("(")+1:-1])
                    if year not in map(lambda i: y + i, range(-1, 2)):
                        continue
                url = self._baseurl + li.a["href"]
                break
            if url is not None:
                break
        del results, h2, ul, li

        subtitles = set()

        if url is None:
            return subtitles

        with self._session.get(url) as response:
            response.raise_for_status()
            html = response.text
        soup = soupify(html).find("div", class_="subtitles")
        del response, html

        header = soup.find("div", class_="box").find("div", class_="header")
        release_name = header.h2.contents[0].strip()
        imdb_id = header.h2.find("a", class_="imdb")["href"]
        imdb_id = imdb_id[imdb_id.rindex("tt"):]
        lendiff = 9 - len(imdb_id)
        if lendiff != 0:
            imdb_id = imdb_id[:2] + lendiff * "0" + imdb_id[2:]
        year = None
        for li in header.ul.children:
            if li.name != "li":
                continue
            if "Year" in li.strong.string:
                year = int(li.strong.next_sibling.strip())
                break

        # if just one language is requested, SSF is available and all the
        # results will be of specified language; no need to parse lang field.
        single_lang = langs.pop() if len(langs) == 1 else None

        for tr in soup.table.tbody.children:
            if tr.name != "tr":
                continue
            a = tr.find("td", class_="a1")
            if a is None:
                continue
            a = a.a
            if single_lang is not None:
                lang = single_lang
            else:
                lang = a.find("span").string.strip()
                try:
                    lang = Language.fromsubscene(lang)
                except NotImplementedError:
                    continue
                if manual_filter and lang not in langs:
                    continue

            page_link = a["href"]
            desc = a.contents[1].string.strip()
            num_files = tr.find("td", class_="a3").string.strip()
            num_files = int(num_files) if num_files else None
            hearing_impaired = tr.find("td", class_="a41") is not None

            subtitles.add(SubsceneSubtitle(lang, hearing_impaired, page_link,
                                           None, desc, None, release_name,
                                           None, imdb_id, num_files, year))

        return subtitles

    def list_subtitles(self, video, languages):
        if isinstance(video, Episode):
            query = "%s - %s Season" % (video.series, to_ordinal[video.season])
        else:
            query = video.title
        return self.query(query, video.year, languages)

    def download_subtitle(self, subtitle):
        logger.info("Downloading subtitle %r", str(subtitle.id))

        url = self._baseurl + subtitle.page_link
        with self._session.get(url) as response:
            response.raise_for_status()
            html = response.text
        link = soupify(html).find("a", {"id": "downloadButton"})

        subtitle.zip_link = link["href"]

        logger.info("Download link: %r", subtitle.zip_link)
        url = self._baseurl + subtitle.zip_link
        with self._session.get(url) as response:
            response.raise_for_status()
            buffer = response.content

        logger.info("Extracting downloaded subtitle")
        with ZipFile(BytesIO(buffer)) as zipfile:
            filenames = zipfile.namelist()
            if subtitle.num_files is not None:
                assert len(filenames) == subtitle.num_files
            else:
                subtitle.num_files = len(filenames)

            if subtitle.num_files == 1:
                filename = filenames[0]
            else:
                # TODO: support multi-file subtitles using guess matching
                raise NotImplementedError()

            assert filename.lower().endswith(".srt")
            content = zipfile.read(filename)
        subtitle.content = fix_line_ending(content)

    def _update_filter(self, langs=set(), hearing_impaired=None):
        """Update cookie-based server-side search filter."""

        new_filter = (langs, hearing_impaired)
        if self._filter == new_filter:
            return

        assert len(langs) <= 3, "Server-side filtering allows no more than " \
            "three languages"

        url = "%s/filter/edit" % self._baseurl
        with self._session.get(url, allow_redirects=False) as response:
            assert response.status_code == 302
            url = response.headers["location"]

        hearing_impaired = {None: 2, True: 1, False: 0}[hearing_impaired]
        langs = sorted(map(lambda l: str(language_ids[l.alpha3]), langs))

        url = url[:url.index("?")]
        data = {"ReturnUrl": "", "SelectedIds": langs, "ForeignOnly": "false",
                "HearingImpaired": hearing_impaired}
        with self._session.post(url, data=data, allow_redirects=False) as resp:
            assert resp.status_code == 302

        self._filter = new_filter
