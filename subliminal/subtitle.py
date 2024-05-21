"""Subtitle class."""

from __future__ import annotations

import codecs
import logging
import os
from typing import TYPE_CHECKING, ClassVar

import chardet
import srt  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from babelfish import Language  # type: ignore[import-untyped]

    from subliminal.video import Video

logger = logging.getLogger(__name__)

#: Subtitle extensions
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.smi', '.txt', '.ssa', '.ass', '.mpl')


class Subtitle:
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
    provider_name: ClassVar[str] = ''

    #: Language of the subtitle
    language: Language

    #: Whether or not the subtitle is hearing impaired
    hearing_impaired: bool

    #: URL of the web page from which the subtitle can be downloaded
    page_link: str | None

    #: Content as bytes
    content: bytes | None

    #: Encoding to decode with when accessing :attr:`text`
    encoding: str | None

    def __init__(
        self,
        language: Language,
        *,
        hearing_impaired: bool = False,
        page_link: str | None = None,
        encoding: str | None = None,
    ) -> None:
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
    def id(self) -> str:
        """Unique identifier of the subtitle."""
        return ''

    @property
    def info(self) -> str:
        """Info of the subtitle, human readable. Usually the subtitle name for GUI rendering."""
        return ''

    @property
    def text(self) -> str:
        """Content as string.

        If :attr:`encoding` is None, the encoding is guessed with :meth:`guess_encoding`

        """
        if not isinstance(self.content, bytes) or not self.content:
            return ''

        # Decode
        if self.encoding:
            return self.content.decode(self.encoding, errors='replace')

        # Get encoding
        guessed_encoding = self.guess_encoding()
        if guessed_encoding:
            return self.content.decode(guessed_encoding, errors='replace')

        # Cannot decode
        logger.warning('Cannot guess encoding to decode subtitle content.')
        return ''

    def is_valid(self) -> bool:
        """Check if a :attr:`text` is a valid SubRip format.

        :return: whether or not the subtitle is valid.
        :rtype: bool

        """
        if not self.text:
            return False

        try:
            self.parsed()
        except srt.SRTParseError:
            return False

        return True

    def parsed(self) -> str:
        """Text content parsed to a valid subtitle."""
        return str(srt.compose(srt.parse(self.text)))

    def guess_encoding(self) -> str | None:
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
        encoding_or_none = chardet.detect(self.content)['encoding']
        logger.info('Chardet found encoding %s', encoding_or_none)

        return encoding_or_none

    def get_path(self, video: Video, *, single: bool = False) -> str:
        """Get the subtitle path using the `video`, `language` and `extension`.

        :param video: path to the video.
        :type video: :class:`~subliminal.video.Video`
        :param bool single: save a single subtitle, default is to save one subtitle per language.
        :return: path of the subtitle.
        :rtype: str

        """
        return get_subtitle_path(video.name, None if single else self.language)

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`.

        :param video: the video to get the matches with.
        :type video: :class:`~subliminal.video.Video`
        :return: matches of the subtitle.
        :rtype: set

        """
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.provider_name + '-' + self.id)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.id!r} [{self.language}]>'


def get_subtitle_path(video_path: str | os.PathLike, language: Language | None = None, extension: str = '.srt') -> str:
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


def fix_line_ending(content: bytes) -> bytes:
    r"""Fix line ending of `content` by changing it to \n.

    :param bytes content: content of the subtitle.
    :return: the content with fixed line endings.
    :rtype: bytes

    """
    return content.replace(b'\r\n', b'\n')
