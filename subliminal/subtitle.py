# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import os.path
import babelfish
import charade
import pysrt
from .video import Episode, Movie


logger = logging.getLogger(__name__)


class Subtitle(object):
    """Base class for subtitle

    :param language: language of the subtitle
    :type language: :class:`babelfish.Language`
    :param bool hearing_impaired: `True` if the subtitle is hearing impaired, `False` otherwise
    :param page_link: link to the web page from which the subtitle can be downloaded, if any
    :type page_link: string or None

    """
    def __init__(self, language, hearing_impaired=False, page_link=None):
        self.language = language
        self.hearing_impaired = hearing_impaired
        self.page_link = page_link

        #: Subtitle's content once downloaded with :meth:`~subliminal.providers.Provider.download_subtitle`
        self.content = None

    def compute_matches(self, video):
        """Compute the matches of the subtitle against the `video`

        :param video: the video to compute the matches against
        :type video: :class:`~subliminal.video.Video`
        :return: matches of the subtitle
        :rtype: set

        """
        raise NotImplementedError

    def compute_score(self, video):
        """Compute the score of the subtitle against the `video`

        There are equivalent matches so that a provider can match one element or its equivalent. This is
        to give all provider a chance to have a score in the same range without hurting quality.

        * Matching :class:`~subliminal.video.Video`'s `hashes` is equivalent to matching everything else
        * Matching :class:`~subliminal.video.Episode`'s `season` and `episode`
          is equivalent to matching :class:`~subliminal.video.Episode`'s `title`
        * Matching :class:`~subliminal.video.Episode`'s `tvdb_id` is equivalent to matching
          :class:`~subliminal.video.Episode`'s `series`

        :param video: the video to compute the score against
        :type video: :class:`~subliminal.video.Video`
        :return: score of the subtitle
        :rtype: int

        """
        score = 0
        # compute matches
        initial_matches = self.compute_matches(video)
        matches = initial_matches.copy()
        # hash is the perfect match
        if 'hash' in matches:
            score = video.scores['hash']
        else:
            # remove equivalences
            if isinstance(video, Episode):
                if 'imdb_id' in matches:
                    matches -= {'series', 'tvdb_id', 'season', 'episode', 'title', 'year'}
                if 'tvdb_id' in matches:
                    matches -= {'series', 'year'}
                if 'title' in matches:
                    matches -= {'season', 'episode'}
            # add other scores
            score += sum((video.scores[match] for match in matches))
        logger.info('Computed score %d with matches %r', score, initial_matches)
        return score

    def __repr__(self):
        return '<%s [%s]>' % (self.__class__.__name__, self.language)


def get_subtitle_path(video_path, language=None):
    """Create the subtitle path from the given `video_path` and `language`

    :param string video_path: path to the video
    :param language: language of the subtitle to put in the path
    :type language: :class:`babelfish.Language` or None
    :return: path of the subtitle
    :rtype: string

    """
    subtitle_path = os.path.splitext(video_path)[0]
    if language is not None:
        try:
            return subtitle_path + '.%s.%s' % (language.alpha2, 'srt')
        except babelfish.LanguageConvertError:
            return subtitle_path + '.%s.%s' % (language.alpha3, 'srt')
    return subtitle_path + '.srt'


def is_valid_subtitle(subtitle_text):
    """Check if a subtitle text is a valid SubRip format

    :return: `True` if the subtitle is valid, `False` otherwise
    :rtype: bool

    """
    try:
        pysrt.from_string(subtitle_text, error_handling=pysrt.ERROR_RAISE)
        return True
    except pysrt.Error as e:
        if e.args[0] > 80:
            return True
    except:
        logger.exception('Unexpected error when validating subtitle')
    return False


def compute_guess_matches(video, guess):
    """Compute matches between a `video` and a `guess`

    :param video: the video to compute the matches on
    :type video: :class:`~subliminal.video.Video`
    :param guess: the guess to compute the matches on
    :type guess: :class:`guessit.Guess`
    :return: matches of the `guess`
    :rtype: set

    """
    matches = set()
    if isinstance(video, Episode):
        # series
        if video.series and 'series' in guess and guess['series'].lower() == video.series.lower():
            matches.add('series')
        # season
        if video.season and 'seasonNumber' in guess and guess['seasonNumber'] == video.season:
            matches.add('season')
        # episode
        if video.episode and 'episodeNumber' in guess and guess['episodeNumber'] == video.episode:
            matches.add('episode')
        # year
        if video.year == guess.get('year'):  # count "no year" as an information
            matches.add('year')
    elif isinstance(video, Movie):
        # year
        if video.year and 'year' in guess and guess['year'] == video.year:
            matches.add('year')
    # title
    if video.title and 'title' in guess and guess['title'].lower() == video.title.lower():
        matches.add('title')
    # release group
    if video.release_group and 'releaseGroup' in guess and guess['releaseGroup'].lower() == video.release_group.lower():
        matches.add('release_group')
    # screen size
    if video.resolution and 'screenSize' in guess and guess['screenSize'] == video.resolution:
        matches.add('resolution')
    # video codec
    if video.video_codec and 'videoCodec' in guess and guess['videoCodec'] == video.video_codec:
        matches.add('video_codec')
    # audio codec
    if video.audio_codec and 'audioCodec' in guess and guess['audioCodec'] == video.audio_codec:
        matches.add('audio_codec')
    return matches


def decode(content, language):
    """Decode subtitle `content` in a specified `language`

    :param bytes content: content of the subtitle
    :param language: language of the subtitle
    :type language: :class:`babelfish.Language`
    :return: the decoded `content` bytes
    :rtype: string

    """
    # always try utf-8 first
    encodings = ['utf-8']

    # add language-specific encodings
    if language.alpha3 == 'zho':
        encodings.extend(['gb18030', 'big5'])
    elif language.alpha3 == 'jpn':
        encodings.append('shift-jis')
    elif language.alpha3 == 'ara':
        encodings.append('windows-1256')
    elif language.alpha3 == 'heb':
        encodings.append('windows-1255')
    else:
        encodings.append('latin-1')

    # try to decode
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            pass

    # fallback on charade
    logger.warning('Could not decode content with encodings %r', encodings)
    return content.decode(charade.detect(content)['encoding'], 'replace')


def fix_line_endings(content):
    """Fix line ending of `content` by changing it to \n

    :param string content: content of the subtitle
    :return: the content with fixed line endings
    :rtype: string

    """
    return content.replace('\r\n', '\n').replace('\r', '\n')
