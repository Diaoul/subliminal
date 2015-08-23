# -*- coding: utf-8 -*-
import logging
import os

import chardet
from guessit.matchtree import MatchTree
from guessit.plugins.transformers import get_transformer
import pysrt

from .video import Episode, Movie

logger = logging.getLogger(__name__)


class Subtitle(object):
    """Base class for subtitle.

    :param language: language of the subtitle.
    :type language: :class:`~babelfish.language.Language`
    :param bool hearing_impaired: whether or not the subtitle is hearing impaired.
    :param page_link: URL of the web page from which the subtitle can be downloaded.
    :type page_link: str

    """
    #: Name of the provider that returns that class of subtitle
    provider_name = ''

    def __init__(self, language, hearing_impaired=False, page_link=None):
        #: Language of the subtitle
        self.language = language

        #: Whether or not the subtitle is hearing impaired
        self.hearing_impaired = hearing_impaired

        #: URL of the web page from which the subtitle can be downloaded
        self.page_link = page_link

        #: Content as bytes
        self.content = None

        #: Encoding to decode with when accessing :attr:`text`
        self.encoding = None

    @property
    def id(self):
        """Unique identifier of the subtitle."""
        raise NotImplementedError

    @property
    def text(self):
        """Content as string.

        If :attr:`encoding` is None, the encoding is guessed with :meth:`guess_encoding`

        """
        if not self.content:
            return

        return self.content.decode(self.encoding or self.guess_encoding(), errors='replace')

    def is_valid(self):
        """Check if a :attr:`text` is a valid SubRip format.

        :return: whether or not the subtitle is valid.
        :rtype: bool

        """
        if not self.text:
            return False

        try:
            pysrt.from_string(self.text, error_handling=pysrt.ERROR_RAISE)
        except pysrt.Error as e:
            if e.args[0] < 80:
                return False

        return True

    def guess_encoding(self):
        """Guess encoding using the language, falling back on chardet.

        :return: the guessed encoding.
        :rtype: str

        """
        logger.info('Guessing encoding for language %s', self.language)

        # always try utf-8 first
        encodings = ['utf-8']

        # add language-specific encodings
        if self.language.alpha3 == 'zho':
            encodings.extend(['gb18030', 'big5'])
        elif self.language.alpha3 == 'jpn':
            encodings.append('shift-jis')
        elif self.language.alpha3 == 'ara':
            encodings.append('windows-1256')
        elif self.language.alpha3 == 'heb':
            encodings.append('windows-1255')
        elif self.language.alpha3 == 'tur':
            encodings.extend(['iso-8859-9', 'windows-1254'])
        elif self.language.alpha3 == 'pol':
            # Eastern European Group 1
            encodings.extend(['windows-1250'])
        elif self.language.alpha3 == 'bul':
            # Eastern European Group 2
            encodings.extend(['windows-1251'])
        else:
            # Western European (windows-1252)
            encodings.append('latin-1')

        # try to decode
        logger.debug('Trying encodings %r', encodings)
        for encoding in encodings:
            try:
                self.content.decode(encoding)
            except UnicodeDecodeError:
                pass
            else:
                logger.info('Guessed encoding %s', encoding)
                return encoding

        logger.warning('Could not guess encoding from language')

        # fallback on chardet
        encoding = chardet.detect(self.content)['encoding']
        logger.info('Chardet found encoding %s', encoding)

        return encoding

    def get_matches(self, video, hearing_impaired=False):
        """Get the matches against the `video`.

        :param video: the video to get the matches with.
        :type video: :class:`~subliminal.video.Video`
        :param bool hearing_impaired: hearing impaired preference.
        :return: matches of the subtitle.
        :rtype: set

        """
        matches = set()

        # hearing_impaired
        if self.hearing_impaired == hearing_impaired:
            matches.add('hearing_impaired')

        return matches

    def __hash__(self):
        return hash(self.provider_name + '-' + self.id)

    def __repr__(self):
        return '<%s %r [%s]>' % (self.__class__.__name__, self.id, self.language)


def compute_score(matches, video, scores=None):
    """Compute the score of the `matches` against the `video`.

    Some matches count as much as a combination of others in order to level the final score:

      * `hash` removes everything else
      * For :class:`~subliminal.video.Episode`

        * `imdb_id` removes `series`, `tvdb_id`, `season`, `episode`, `title` and `year`
        * `tvdb_id` removes `series` and `year`
        * `title` removes `season` and `episode`


    :param video: the video to get the score with.
    :type video: :class:`~subliminal.video.Video`
    :param dict scores: scores to use, if `None`, the :attr:`~subliminal.video.Video.scores` from the video are used.
    :return: score of the subtitle.
    :rtype: int

    """
    final_matches = matches.copy()
    scores = scores or video.scores

    logger.info('Computing score for matches %r and %r', matches, video)

    # remove equivalent match combinations
    if 'hash' in final_matches:
        final_matches &= {'hash', 'hearing_impaired'}
    elif isinstance(video, Episode):
        if 'imdb_id' in final_matches:
            final_matches -= {'series', 'tvdb_id', 'season', 'episode', 'title', 'year'}
        if 'tvdb_id' in final_matches:
            final_matches -= {'series', 'year'}
        if 'title' in final_matches:
            final_matches -= {'season', 'episode'}

    # compute score
    logger.debug('Final matches: %r', final_matches)
    score = sum((scores[match] for match in final_matches))
    logger.info('Computed score %d', score)

    # ensure score is capped by the best possible score (hash + preferences)
    assert score <= scores['hash'] + scores['hearing_impaired']

    return score


def get_subtitle_path(video_path, language=None, extension='.srt'):
    """Get the subtitle path using the `video_path` and `language`.

    :param str video_path: path to the video.
    :param language: language of the subtitle to put in the path.
    :type language: :class:`~babelfish.language.Language`
    :param str extension: extension of the subtitle.
    :return: path of the subtitle.
    :rtype: str

    """
    subtitle_root = os.path.splitext(video_path)[0]

    if language:
        subtitle_root += '.' + str(language)

    return subtitle_root + extension


def guess_matches(video, guess, partial=False):
    """Get matches between a `video` and a `guess`.

    If a guess is `partial`, the absence information won't be counted as a match.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param guess: the guess.
    :type guess: dict
    :param bool partial: whether or not the guess is partial.
    :return: matches between the `video` and the `guess`.
    :rtype: set

    """
    matches = set()
    if isinstance(video, Episode):
        # series
        if video.series and 'series' in guess and guess['series'].lower() == video.series.lower():
            matches.add('series')
        # season
        if video.season and 'season' in guess and guess['season'] == video.season:
            matches.add('season')
        # episode
        if video.episode and 'episodeNumber' in guess and guess['episodeNumber'] == video.episode:
            matches.add('episode')
        # year
        if video.year and 'year' in guess and guess['year'] == video.year:
            matches.add('year')
        # count "no year" as an information
        if not partial and video.year is None and 'year' not in guess:
            matches.add('year')
    elif isinstance(video, Movie):
        # year
        if video.year and 'year' in guess and guess['year'] == video.year:
            matches.add('year')
    # title
    if video.title and 'title' in guess and guess['title'].lower() == video.title.lower():
        matches.add('title')
    # release_group
    if video.release_group and 'releaseGroup' in guess and guess['releaseGroup'].lower() == video.release_group.lower():
        matches.add('release_group')
    # resolution
    if video.resolution and 'screenSize' in guess and guess['screenSize'] == video.resolution:
        matches.add('resolution')
    # format
    if video.format and 'format' in guess and guess['format'].lower() == video.format.lower():
        matches.add('format')
    # video_codec
    if video.video_codec and 'videoCodec' in guess and guess['videoCodec'] == video.video_codec:
        matches.add('video_codec')
    # audio_codec
    if video.audio_codec and 'audioCodec' in guess and guess['audioCodec'] == video.audio_codec:
        matches.add('audio_codec')

    return matches


def guess_properties(string):
    """Extract properties from `string` using guessit's `guess_properties` transformer.

    :param str string: the string potentially containing properties.
    :return: the guessed properties.
    :rtype: dict

    """
    mtree = MatchTree(string)
    get_transformer('guess_properties').process(mtree)

    return mtree.matched()


def fix_line_ending(content):
    """Fix line ending of `content` by changing it to \n.

    :param bytes content: content of the subtitle.
    :return: the content with fixed line endings.
    :rtype: bytes

    """
    return content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
