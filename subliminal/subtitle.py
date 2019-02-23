# -*- coding: utf-8 -*-
import codecs
import logging
import os

import chardet
import pysrt

from six import text_type

logger = logging.getLogger(__name__)

#: Subtitle extensions
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.smi', '.txt', '.ssa', '.ass', '.mpl')


class Subtitle(object):
    """Base class for subtitle.

    :param language: language of the subtitle.
    :type language: :class:`~babelfish.language.Language`
    :param bool hearing_impaired: whether or not the subtitle is hearing impaired.
    :param page_link: URL of the web page from which the subtitle can be downloaded.
    :type page_link: str
    :param encoding: Text encoding of the subtitle.
    :type encoding: str

    """
    #: Name of the provider that returns that class of subtitle
    provider_name = ''

    def __init__(self, language, hearing_impaired=False, page_link=None, encoding=None):
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

        # validate the encoding
        if encoding:
            try:
                self.encoding = codecs.lookup(encoding).name
            except (TypeError, LookupError):
                logger.debug('Unsupported encoding %s', encoding)

    @property
    def id(self):
        """Unique identifier of the subtitle"""
        raise NotImplementedError

    @property
    def info(self):
        """Info of the subtitle, human readable. Usually the subtitle name for GUI rendering"""
        raise NotImplementedError

    @property
    def text(self):
        """Content as string

        If :attr:`encoding` is None, the encoding is guessed with :meth:`guess_encoding`

        """
        if not self.content:
            return

        if not isinstance(self.content, text_type):
            if self.encoding:
                return self.content.decode(self.encoding, errors='replace')

            guessed_encoding = self.guess_encoding()
            if guessed_encoding:
                return self.content.decode(guessed_encoding, errors='replace')

            return None

        return self.content

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

    def get_path(self, video, single=False):
        """Get the subtitle path using the `video`, `language` and `extension`.

        :param video: path to the video.
        :type video: :class:`~subliminal.video.Video`
        :param bool single: save a single subtitle, default is to save one subtitle per language.
        :return: path of the subtitle.
        :rtype: str

        """
        return get_subtitle_path(video.name, None if single else self.language)

    def get_matches(self, video):
        """Get the matches against the `video`.

        :param video: the video to get the matches with.
        :type video: :class:`~subliminal.video.Video`
        :return: matches of the subtitle.
        :rtype: set

        """
        raise NotImplementedError

    def __hash__(self):
        return hash(self.provider_name + '-' + self.id)

    def __repr__(self):
        return '<%s %r [%s]>' % (self.__class__.__name__, self.id, self.language)


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


def fix_line_ending(content):
    """Fix line ending of `content` by changing it to \n.

    :param bytes content: content of the subtitle.
    :return: the content with fixed line endings.
    :rtype: bytes

    """
    return content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
