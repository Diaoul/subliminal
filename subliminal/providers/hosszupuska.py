# -*- coding: utf-8 -*-
import io
import logging
import re
from zipfile import ZipFile

from babelfish import Language, language_converters
from requests import Session

from . import ParserBeautifulSoup, Provider
from ..exceptions import ProviderError
from ..score import get_equivalent_release_groups
from ..subtitle import Subtitle, fix_line_ending
from ..utils import sanitize, sanitize_release_group
from ..video import Episode

logger = logging.getLogger(__name__)

language_converters.register('hosszupuska = subliminal.converters.hosszupuska:HosszupuskaConverter')

# link_re = re.compile(r'^(?P<series>.+?)(?: \(?\d{4}\)?| \((?:US|UK)\))? \((?P<first_year>\d{4})-\d{4}\)$')
# episode_id_re = re.compile(r'^episode-\d+\.html$')


class HosszupuskaSubtitle(Subtitle):
    """Hosszupuska Subtitle."""
    provider_name = 'hosszupuska'

    def __str__(self):
        subtit = "Subtitle id: " + self.subtitle_id \
               + " Series: " + self.series \
               + " Season: " + self.season \
               + " Episode: " + self.episode \
               + " Release_group: " + self.release_group + " "
        if self.format:
            subtit = subtit + " Format: " + self.format + " "
        if self.resolution:
            subtit = subtit + " Resolution: " + self.resolution
        if self.date:
            subtit = subtit + " Year: " + self.year
        return subtit.encode('utf-8')

    def __init__(self, language, page_link, subtitle_id, series, season, episode,
                 format, release_group, resolution, date):
        super(HosszupuskaSubtitle, self).__init__(language, page_link=page_link)
        self.subtitle_id = subtitle_id
        self.series = series
        self.season = season
        self.episode = episode
        self.format = format
        self.release_group = release_group
        self.resolution = resolution
        self.date = date
        self.year = None
        if self.date:
            self.year = date.strip().split('-')[0]

    @property
    def id(self):
        return str(self.subtitle_id)

    def get_matches(self, video):
        matches = set()
        # series
        if video.series and sanitize(self.series) == sanitize(video.series):
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        # year
        if self.year and video.year and video.year == self.year:
            matches.add('year')
        # resolution
        if video.resolution and self.resolution and video.resolution == self.resolution:
            matches.add('resolution')
        # release_group
        if (video.release_group and self.release_group and
                any(r in sanitize_release_group(self.release_group)
                    for r in get_equivalent_release_groups(sanitize_release_group(video.release_group)))):
                        matches.add('release_group')
        # other properties
        if video.format and self.format and video.format.lower() == self.format.lower():
            matches.add('format')

        return matches


class HosszupuskaProvider(Provider):
    """Hosszupuska Provider."""
    languages = {Language('hun', 'HU')} | {Language(l) for l in [
        'hun', 'eng'
    ]}
    video_types = (Episode,)
    server_url = 'http://hosszupuskasub.com/'

    def initialize(self):
        self.session = Session()
        # self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__

    def terminate(self):
        self.session.close()

    def GetLanguage(self, text):
        if text == '1.gif':
            return Language.fromhosszupuska('hu')
        if text == '2.gif':
            return Language.fromhosszupuska('en')
        return Language.fromhosszupuska.hu

    def query(self, series, season, episode, year=None):

        # Search for s01e03 instead of s1e3
        if season < 10:
            seasona = '0'+str(season)
        else:
            seasona = str(season)
        if episode < 10:
            episodea = '0'+str(episode)
        else:
            episodea = str(episode)
        season = seasona
        episode = episodea

        # get the episode page
        logger.info('Getting the page for episode %d', episode)
        url = self.server_url + "sorozatok.php?cim=" + series.replace(' ', '+') + "&evad="+str(seasona) + \
            "&resz="+str(episodea)+"&nyelvtipus=%25&x=24&y=8"

        # scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance
        # Or: scraper = cfscrape.CloudflareScraper()  # CloudflareScraper inherits from requests.Session
        # r = scraper.get(url).content
        # file = open('testfile.txt','r')
        # r = file.read();

        r = self.session.get(url, timeout=10).content
        soup = ParserBeautifulSoup(r, ['lxml', 'html.parser'])

        subtitles = []
        table = soup.find_all("table")[9]

        # loop over subtitles rows
        i = 0
        for row in table.find_all("tr"):
            i = i + 1
            if "this.style.backgroundImage='url(css/over2.jpg)" in str(row) and i > 5:
                datas = row.find_all("td")

                # Currently subliminal only use English name but Hungarian can be parsed like this:
                # hunagrian_name = re.split('s(\d{1,2})', datas[1].find_all('b')[0].getText())[0]
                # sub_translator = datas[3].getText()

                # Handle the case when '(' in subtitle
                if datas[1].getText().count('(') == 1:
                    sub_english_name = re.split('s(\d{1,2})e(\d{1,2})', datas[1].getText().split('(')[0])[3]
                if datas[1].getText().count('(') == 2:
                    sub_english_name = re.split('s(\d{1,2})e(\d{1,2})', datas[1].getText().split('(')[0] +
                                                datas[1].getText().split('(')[1])[3]
                sub_season = re.findall('s(\d{1,2})', datas[1].find_all('b')[0].getText(), re.VERBOSE)[0]
                sub_episode = re.findall('e(\d{1,2})', datas[1].find_all('b')[0].getText(), re.VERBOSE)[0]
                sub_language = self.GetLanguage(datas[2].find_all('img')[0]['src'].split('/')[1])
                sub_downloadlink = datas[6].find_all('a')[1]['href']
                sub_id = sub_downloadlink.split('=')[1].split('.')[0]
                sub_date = datas[4].getText()
                if datas[1].getText().count('(') == 1:
                    sub_version = datas[1].getText().split('(')[1].split(')')[0]
                if datas[1].getText().count('(') == 2:
                    sub_version = datas[1].getText().split('(')[2].split(')')[0]

                # One subtitle can be used for sevearl relase add both of them.
                sub_releases = sub_version.split(',')
                for release in sub_releases:
                    if ('-' in release.strip()):
                        sub_release_group = (release.strip()).split('-')[1]
                        sub_resolution = (release.strip()).split('-')[0]
                        if ('0p' not in sub_resolution):
                            sub_format = sub_resolution
                            sub_resolution = None
                        else:
                            sub_format = None
                    else:
                        sub_release_group = release
                        sub_resolution = None
                        sub_format = None
                    subtitle = HosszupuskaSubtitle(sub_language, sub_downloadlink, sub_id, sub_english_name, sub_season,
                                                   sub_episode, sub_format, sub_release_group, sub_resolution, sub_date)

                    # Currently rar is not supported (But not commonly used on the provider)
                    if 'rar' not in sub_downloadlink and sub_season == season and sub_episode == episode:
                        logger.debug('Found subtitle \r\n%s', subtitle)
                        subtitles.append(subtitle)
        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season, video.episode, video.year) if s.language in languages]

    def download_subtitle(self, subtitle):

        # download as a zip
        logger.info('Downloading subtitle %r', subtitle.subtitle_id)
        r = self.session.get(subtitle.page_link, timeout=10)
        r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
