from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.subtitle import (
    EmbeddedSubtitle,
    ExternalSubtitle,
    LanguageType,
    Subtitle,
    fix_line_ending,
    get_subtitle_path,
    get_subtitle_suffix,
)

if TYPE_CHECKING:
    from subliminal.video import Movie

# Core test
pytestmark = pytest.mark.core


@pytest.mark.parametrize('hearing_impaired', [None, True, False])
@pytest.mark.parametrize('foreign_only', [None, True, False])
def test_languague_type(hearing_impaired: bool | None, foreign_only: bool | None) -> None:
    language_type = LanguageType.from_flags(hearing_impaired=hearing_impaired, foreign_only=foreign_only)

    if hearing_impaired is True:
        assert language_type == LanguageType.HEARING_IMPAIRED
        assert language_type.is_hearing_impaired() is True
        assert language_type.is_foreign_only() is False
    elif foreign_only is True:
        assert language_type == LanguageType.FOREIGN_ONLY
        assert language_type.is_hearing_impaired() is False
        assert language_type.is_foreign_only() is True
    elif hearing_impaired is False or foreign_only is False:
        assert language_type == LanguageType.NORMAL
        assert language_type.is_hearing_impaired() is False
        assert language_type.is_foreign_only() is False
    else:
        assert language_type == LanguageType.UNKNOWN
        assert language_type.is_hearing_impaired() is None
        assert language_type.is_foreign_only() is None


def test_subtitle_text() -> None:
    subtitle = Subtitle(Language('eng'))
    subtitle.set_content(b'Some ascii text')
    assert subtitle.text == 'Some ascii text'


def test_subtitle_text_no_content() -> None:
    subtitle = Subtitle(Language('eng'))
    assert subtitle.text == ''


def test_subtitle_none_content() -> None:
    subtitle = Subtitle(Language('jpn'))
    subtitle.set_content(None)
    assert subtitle.is_valid() is False


def test_subtitle_guess_format(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(Language('jpn'))
    text = '1\n2\n間違ったサブタイトル'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is False


def test_subtitle_other_subtitle_format(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(Language('jpn'), subtitle_format='vtt')
    text = '1\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_no_content() -> None:
    subtitle = Subtitle(Language('fra'))
    assert subtitle.is_valid() is False


def test_subtitle_is_valid_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(Language('fra'))
    text = "1\n00:00:20,000 --> 00:00:24,400\nEn réponse à l'augmentation de la criminalité\ndans certains quartiers,\n"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'srt'


def test_subtitle_is_valid_auto_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(Language('fra'), auto_fix_srt=True)
    text = (
        "1\n00:00:20,000 --> 00:00:24,400\nEn réponse à l'augmentation de la criminalité\ndans certains quartiers,\n\n"
    )
    text += "This line shouldn't be here"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_valid_begin(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(Language('fra'))
    text = (
        "1\n00:00:20,000 --> 00:00:24,400\nEn réponse à l'augmentation de la criminalité\ndans certains quartiers,\n\n"
    ) * 20
    text += "This line shouldn't be here"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_sub_format(monkeypatch: pytest.MonkeyPatch, movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    subtitle = Subtitle(Language('pol'))
    text = '{3146}{3189}/Nie rozumiecie?\n{3189}{3244}/Jšdro Kryptona się rozpada.\n{3244}{3299}To kwestia tygodni.\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'microdvd'
    path = subtitle.get_path(video, single=True)
    extension = os.path.splitext(path)[1]
    assert extension == '.sub'


def test_subtitle_get_path_extension(monkeypatch: pytest.MonkeyPatch, movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    subtitle = Subtitle(Language('pol'))
    text = '{3146}{3189}/Nie rozumiecie?\n{3189}{3244}/Jšdro Kryptona się rozpada.\n{3244}{3299}To kwestia tygodni.\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'microdvd'
    path = subtitle.get_path(video, single=True, extension='.srt')
    extension = os.path.splitext(path)[1]
    assert extension == '.srt'


def test_get_subtitle_path(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, extension='.sub') == os.path.splitext(video.name)[0] + '.sub'


def test_get_subtitle_path_language(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('por', 'BR'))
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.pt-BR.srt'


def test_get_subtitle_path_language_undefined(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('und'))
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.srt'


def test_get_subtitle_path_hearing_impaired(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(
        Language('deu', 'CH', 'Latn'),
        language_type=LanguageType.HEARING_IMPAIRED,
        language_type_suffix=True,
    )
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.[hi].de-CH-Latn.srt'


def test_get_subtitle_path_foreign_only(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(
        Language('srp', None, 'Cyrl'),
        language_type=LanguageType.FOREIGN_ONLY,
        language_type_suffix=True,
    )
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.[fo].sr-Cyrl.srt'


def test_get_subtitle_path_foreign_only_language_first(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(
        Language('srp', None, 'Cyrl'),
        language_type=LanguageType.FOREIGN_ONLY,
        language_type_suffix=True,
        language_first=True,
    )
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.sr-Cyrl.[fo].srt'


def test_get_subtitle_path_alpha3(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('fra', 'CA'), language_format='alpha3')
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.fra-CA.srt'


def test_get_subtitle_path_extension(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('zho', 'CN'), language_type_suffix=True)
    assert get_subtitle_path(video.name, suffix, extension='.sub') == os.path.splitext(video.name)[0] + '.zh-CN.sub'


def test_fix_line_ending() -> None:
    content = b'Text\r\nwith\r\nweird\nline ending\r\ncharacters'
    assert fix_line_ending(content) == b'Text\nwith\nweird\nline ending\ncharacters'


# https://github.com/pannal/Sub-Zero.bundle/issues/646 replaced all Chinese character “不” with “上”
def test_fix_line_ending_chinese_characters() -> None:
    character = bytes('不', 'utf-16-le')
    content = b''.join([character, b'\r\n', character, b'\n', character])
    expected = b''.join([character, b'\n', character, b'\n', character])
    assert fix_line_ending(content) == expected


def test_subtitle_valid_encoding() -> None:
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding='windows-1252',
    )
    assert subtitle.encoding == 'cp1252'


def test_subtitle_empty_encoding() -> None:
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding=None,
    )
    assert subtitle.encoding is None


def test_subtitle_invalid_encoding() -> None:
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding='rubbish',
    )
    assert subtitle.encoding is None
    assert subtitle.hearing_impaired is False


def test_subtitle_set_content() -> None:
    subtitle = Subtitle(language=Language('kur'), encoding=None)
    content = b'Ti\xc5\x9ftek li vir'
    subtitle.content = content
    assert subtitle.content == content
    assert subtitle.text == content.decode()


def test_subtitle_guess_encoding_utf8() -> None:
    subtitle = Subtitle(
        language=Language('zho'),
        foreign_only=False,
        page_link=None,
        encoding=None,
    )
    subtitle.set_content(b'Something here')
    assert subtitle.foreign_only is False
    assert subtitle.guess_encoding() == 'utf-8'
    assert subtitle.text == 'Something here'


# regression for #921
def test_subtitle_text_guess_encoding_none() -> None:
    content = b'\x00d\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff,\x00\x00\x00\x00d\x00d\x00\x00\x02s\x84\x8f\xa9'
    subtitle = Subtitle(
        language=Language('zho'),
        hearing_impaired=False,
        page_link=None,
        encoding=None,
    )
    subtitle.set_content(content)

    assert subtitle.guess_encoding() is None
    assert not subtitle.is_valid()
    assert subtitle.text == ''


def test_subtitle_reencode() -> None:
    content = b'Uma palavra longa \xe9 melhor do que um p\xe3o curto'
    subtitle = Subtitle(
        language=Language('por'),
        encoding='latin1',
    )
    subtitle.set_content(content)
    success = subtitle.reencode()
    assert success
    assert subtitle.content == b'Uma palavra longa \xc3\xa9 melhor do que um p\xc3\xa3o curto'


def test_subtitle_reencode_text() -> None:
    text = 'Uma palavra longa é melhor do que um pão curto'
    subtitle = Subtitle(
        language=Language('por'),
        encoding='latin1',
    )

    assert not subtitle.text

    success = subtitle.reencode(text)
    assert success
    assert subtitle.content == b'Uma palavra longa \xc3\xa9 melhor do que um p\xc3\xa3o curto'
    assert subtitle.text == text


def test_subtitle_convert_empty() -> None:
    subtitle = Subtitle(
        language=Language('fra'),
        encoding='latin1',
    )
    assert not subtitle.convert()


def test_subtitle_convert_same_format_same_encoding() -> None:
    subtitle = Subtitle(
        language=Language('eng'),
        encoding='utf-8',
    )
    text = "1\n00:00:05,000 --> 00:00:10,000\n«Attention, ce flim n'est pas un flim sur le cyclimse»\n\n"
    subtitle.set_content(text.encode('utf-8'))
    assert subtitle.encoding == 'utf-8'
    assert subtitle.text == text

    assert subtitle.convert(output_format='srt', output_encoding=None)


def test_subtitle_convert_same_format_different_encoding() -> None:
    subtitle = Subtitle(
        language=Language('fra'),
        encoding='latin1',
    )
    text = "1\n00:00:05,000 --> 00:00:10,000\n«Attention, ce flim n'est pas un flim sur le cyclimse»\n\n"
    subtitle.set_content(text.encode('latin1'))
    assert subtitle.encoding == 'iso8859-1'
    assert subtitle.text == text

    assert subtitle.convert(output_format='srt', output_encoding='utf-8')
    assert subtitle.encoding == 'utf-8'
    assert subtitle.text == text


def test_subtitle_convert_from_microdvd_no_fps() -> None:
    subtitle = Subtitle(
        language=Language('pol'),
    )
    text = """\
    {1189}{1271}Tłumaczenie:|sinu6
    {3146}{3189}/Nie rozumiecie?
    {3189}{3244}/Jądro Kryptona się rozpada.
    {3244}{3299}To kwestia tygodni.
    {3299}{3390}Ostrzegałem, że eksploatacja jądra|to samobójstwo.
    """
    subtitle.set_content(text.encode('utf-8'))

    assert not subtitle.convert(output_format='srt', output_encoding='utf-8')


def test_subtitle_convert_from_microdvd_subtitle_fps() -> None:
    subtitle = Subtitle(
        language=Language('pol'),
        fps=24,
    )
    text = """\
    {1189}{1271}Tłumaczenie:|sinu6
    {3146}{3189}/Nie rozumiecie?
    {3189}{3244}/Jądro Kryptona się rozpada.
    {3244}{3299}To kwestia tygodni.
    {3299}{3390}Ostrzegałem, że eksploatacja jądra|to samobójstwo.
    """
    subtitle.set_content(text.encode('utf-8'))

    assert subtitle.convert(output_format='srt', output_encoding='utf-8')
    assert subtitle.subtitle_format == 'srt'
    assert subtitle.encoding == 'utf-8'

    new_text = dedent(
        """\
        1
        00:00:49,542 --> 00:00:52,958
        Tłumaczenie:
        sinu6

        2
        00:02:11,083 --> 00:02:12,875
        /Nie rozumiecie?

        3
        00:02:12,875 --> 00:02:15,167
        /Jądro Kryptona się rozpada.

        4
        00:02:15,167 --> 00:02:17,458
        To kwestia tygodni.

        5
        00:02:17,458 --> 00:02:21,250
        Ostrzegałem, że eksploatacja jądra
        to samobójstwo.

        """
    )
    assert subtitle.text == new_text


def test_subtitle_convert_from_microdvd_argument_fps() -> None:
    subtitle = Subtitle(
        language=Language('pol'),
        fps=32,
    )
    text = """\
    {1189}{1271}Tłumaczenie:|sinu6
    {3146}{3189}/Nie rozumiecie?
    {3189}{3244}/Jądro Kryptona się rozpada.
    {3244}{3299}To kwestia tygodni.
    {3299}{3390}Ostrzegałem, że eksploatacja jądra|to samobójstwo.
    """
    subtitle.set_content(text.encode('utf-8'))

    assert subtitle.convert(output_format='srt', output_encoding='utf-8', fps=24)
    assert subtitle.subtitle_format == 'srt'
    assert subtitle.encoding == 'utf-8'

    new_text = dedent(
        """\
        1
        00:00:49,542 --> 00:00:52,958
        Tłumaczenie:
        sinu6

        2
        00:02:11,083 --> 00:02:12,875
        /Nie rozumiecie?

        3
        00:02:12,875 --> 00:02:15,167
        /Jądro Kryptona się rozpada.

        4
        00:02:15,167 --> 00:02:17,458
        To kwestia tygodni.

        5
        00:02:17,458 --> 00:02:21,250
        Ostrzegałem, że eksploatacja jądra
        to samobójstwo.

        """
    )
    assert subtitle.text == new_text


def test_subtitle_convert_to_ssa() -> None:
    subtitle = Subtitle(
        language=Language('pol'),
        fps=24,
    )
    text = dedent(
        """\
        1
        00:00:49,542 --> 00:00:52,958
        Tłumaczenie:
        sinu6

        2
        00:02:11,083 --> 00:02:12,875
        /Nie rozumiecie?

        3
        00:02:12,875 --> 00:02:15,167
        /Jądro Kryptona się rozpada.

        4
        00:02:15,167 --> 00:02:17,458
        To kwestia tygodni.

        5
        00:02:17,458 --> 00:02:21,250
        Ostrzegałem, że eksploatacja jądra
        to samobójstwo.

        """
    )
    subtitle.set_content(text.encode('utf-8'))

    assert subtitle.convert(output_format='ass')
    assert subtitle.subtitle_format == 'ass'
    assert subtitle.encoding == 'utf-8'

    # Define a variable to be able to wrap the long line
    styles = (
        'Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, '
        'Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, '
        'Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding'
    )
    new_text = dedent(
        f"""\
        [Script Info]
        ; Script generated by pysubs2
        ; https://pypi.python.org/pypi/pysubs2
        WrapStyle: 0
        ScaledBorderAndShadow: yes
        Collisions: Normal
        ScriptType: v4.00+

        [V4+ Styles]
        Format: {styles}
        Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        Dialogue: 0,0:00:49.54,0:00:52.96,Default,,0,0,0,,Tłumaczenie:\\Nsinu6
        Dialogue: 0,0:02:11.08,0:02:12.88,Default,,0,0,0,,/Nie rozumiecie?
        Dialogue: 0,0:02:12.88,0:02:15.17,Default,,0,0,0,,/Jądro Kryptona się rozpada.
        Dialogue: 0,0:02:15.17,0:02:17.46,Default,,0,0,0,,To kwestia tygodni.
        Dialogue: 0,0:02:17.46,0:02:21.25,Default,,0,0,0,,Ostrzegałem, że eksploatacja jądra\\Nto samobójstwo.
        """
    )
    assert subtitle.text == new_text


def test_subtitle_info(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = Subtitle(
        Language('eng'),
        'xv34e',
        foreign_only=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nIn response to your honored\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_embedded_subtitle_info(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = EmbeddedSubtitle(
        Language('ita'),
        subtitle_id='test_embedded_subtitle_info',
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nIn risposta alla sua lettera del\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_embedded_subtitle_info_hearing_impaired(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = EmbeddedSubtitle(
        Language('spa'),
        subtitle_id='test_embedded_subtitle_info_hearing_impaired',
        hearing_impaired=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn respuesta a su carta de\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.hearing_impaired is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_embedded_subtitle_info_foreign_only(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = EmbeddedSubtitle(
        Language('fra'),
        subtitle_id='test_embedded_subtitle_info_foreign_only',
        foreign_only=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn réponse à votre honorée du tant\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.foreign_only is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_external_subtitle_from_language_code(monkeypatch: pytest.MonkeyPatch) -> None:
    filename = 'test_external_subtitle_from_language_code'
    subtitle = ExternalSubtitle.from_language_code('fr', subtitle_path=filename)
    assert subtitle.language == Language('fra')
    assert subtitle.id == 'test_external_subtitle_from_language_code'
    assert not subtitle.language_type.is_hearing_impaired()
    assert not subtitle.language_type.is_foreign_only()
    assert subtitle.subtitle_format is None


def test_external_subtitle_from_language_code_hearing_impaired(monkeypatch: pytest.MonkeyPatch) -> None:
    filename = Path('filename.[hi].eng.ass')
    subtitle = ExternalSubtitle.from_language_code('[hi].eng', subtitle_path=filename)
    assert subtitle.language == Language('eng')
    assert subtitle.language_type.is_hearing_impaired()
    assert subtitle.id == os.fspath(filename)
    assert subtitle.subtitle_format == 'ass'


def test_external_subtitle_from_language_code_foreign_only(monkeypatch: pytest.MonkeyPatch) -> None:
    filename = Path('filename.hu.[fo].srt')
    subtitle = ExternalSubtitle.from_language_code('hu.fo', subtitle_path=filename)
    assert subtitle.language == Language('hun')
    assert subtitle.language_type.is_foreign_only()
    assert subtitle.id == os.fspath(filename)
    assert subtitle.subtitle_format == 'srt'


def test_external_subtitle_from_language_code_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    filename = Path('filename.hi.fo.srt')
    subtitle = ExternalSubtitle.from_language_code('hi.fo', subtitle_path=filename)
    # Hearing impaired code 'hi' is matched first
    assert subtitle.language == Language('fao')
    assert subtitle.language_type.is_hearing_impaired()
    assert subtitle.id == os.fspath(filename)
    assert subtitle.subtitle_format == 'srt'


def test_external_subtitle_info(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = ExternalSubtitle(
        Language('ita'),
        subtitle_id='test_embedded_subtitle_info',
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nIn risposta alla sua lettera del\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_external_subtitle_info_hearing_impaired(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = ExternalSubtitle(
        Language('spa'),
        subtitle_id='test_embedded_subtitle_info_hearing_impaired',
        hearing_impaired=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn respuesta a su carta de\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.hearing_impaired is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_external_subtitle_info_foreign_only(monkeypatch: pytest.MonkeyPatch) -> None:
    subtitle = ExternalSubtitle(
        Language('fra'),
        subtitle_id='test_external_subtitle_info_foreign_only',
        foreign_only=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn réponse à votre honorée du tant\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.foreign_only is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_subtitle_hash() -> None:
    subtitle = Subtitle(
        Language('eng'),
        'xv34e',
    )
    external_subtitle = ExternalSubtitle(
        Language('fra'),
        subtitle_id='video-HD.[fo].fr.srt',
        foreign_only=True,
    )
    embedded_subtitle = EmbeddedSubtitle(
        Language('spa'),
        subtitle_id='video-HD.mkv',
        hearing_impaired=True,
    )
    subtitle_set = {subtitle, external_subtitle, embedded_subtitle}
    assert len(subtitle_set) == 3
    assert subtitle in subtitle_set
    assert external_subtitle in subtitle_set
    assert embedded_subtitle in subtitle_set
