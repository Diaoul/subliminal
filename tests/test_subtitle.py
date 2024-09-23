from __future__ import annotations

import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from subliminal.subtitle import (
    EmbeddedSubtitle,
    LanguageType,
    Subtitle,
    fix_line_ending,
    get_subtitle_path,
    get_subtitle_suffix,
)

# Core test
pytestmark = pytest.mark.core


@pytest.mark.parametrize('hearing_impaired', [None, True, False])
@pytest.mark.parametrize('forced', [None, True, False])
def test_languague_type(hearing_impaired: bool | None, forced: bool | None) -> None:
    language_type = LanguageType.from_flags(hearing_impaired=hearing_impaired, forced=forced)

    if hearing_impaired is True:
        assert language_type == LanguageType.HEARING_IMPAIRED
        assert language_type.is_hearing_impaired() is True
        assert language_type.is_forced() is False
    elif forced is True:
        assert language_type == LanguageType.FORCED
        assert language_type.is_hearing_impaired() is False
        assert language_type.is_forced() is True
    elif hearing_impaired is False or forced is False:
        assert language_type == LanguageType.NORMAL
        assert language_type.is_hearing_impaired() is False
        assert language_type.is_forced() is False
    else:
        assert language_type == LanguageType.UNKNOWN
        assert language_type.is_hearing_impaired() is None
        assert language_type.is_forced() is None


def test_subtitle_text() -> None:
    subtitle = Subtitle(Language('eng'))
    subtitle.content = b'Some ascii text'
    assert subtitle.text == 'Some ascii text'


def test_subtitle_text_no_content() -> None:
    subtitle = Subtitle(Language('eng'))
    assert subtitle.text == ''


def test_subtitle_none_content() -> None:
    subtitle = Subtitle(Language('jpn'))
    subtitle.content = None
    assert subtitle.is_valid() is False


def test_subtitle_guess_format(monkeypatch) -> None:
    subtitle = Subtitle(Language('jpn'))
    text = '1\n2\n間違ったサブタイトル'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is False


def test_subtitle_other_subtitle_format(monkeypatch) -> None:
    subtitle = Subtitle(Language('jpn'))
    subtitle.subtitle_format = 'vtt'
    text = '1\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_no_content() -> None:
    subtitle = Subtitle(Language('fra'))
    assert subtitle.is_valid() is False


def test_subtitle_is_valid_valid(monkeypatch) -> None:
    subtitle = Subtitle(Language('fra'))
    text = (
        '1\n'
        '00:00:20,000 --> 00:00:24,400\n'
        "En réponse à l'augmentation de la criminalité\n"
        'dans certains quartiers,\n'
    )
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'srt'


def test_subtitle_is_valid_auto_fix(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (
        '1\n'
        '00:00:20,000 --> 00:00:24,400\n'
        "En réponse à l'augmentation de la criminalité\n"
        'dans certains quartiers,\n\n'
    )
    text += "This line shouldn't be here"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid(auto_fix_srt=True) is True


def test_subtitle_is_valid_valid_begin(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (
        '1\n'
        '00:00:20,000 --> 00:00:24,400\n'
        "En réponse à l'augmentation de la criminalité\n"
        'dans certains quartiers,\n\n'
    ) * 20
    text += "This line shouldn't be here"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_sub_format(monkeypatch, movies):
    video = movies['man_of_steel']
    subtitle = Subtitle(Language('pol'))
    text = (
        '{3146}{3189}/Nie rozumiecie?\n'
        '{3189}{3244}/Jšdro Kryptona się rozpada.\n'
        '{3244}{3299}To kwestia tygodni.\n'
    )
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'microdvd'
    path = subtitle.get_path(video, single=True)
    extension = os.path.splitext(path)[1]
    assert extension == '.sub'


def test_subtitle_get_path_extension(monkeypatch, movies):
    video = movies['man_of_steel']
    subtitle = Subtitle(Language('pol'))
    text = (
        '{3146}{3189}/Nie rozumiecie?\n'
        '{3189}{3244}/Jšdro Kryptona się rozpada.\n'
        '{3244}{3299}To kwestia tygodni.\n'
    )
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert subtitle.subtitle_format == 'microdvd'
    path = subtitle.get_path(video, single=True, extension='.srt')
    extension = os.path.splitext(path)[1]
    assert extension == '.srt'


def test_get_subtitle_path(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, extension='.sub') == os.path.splitext(video.name)[0] + '.sub'


def test_get_subtitle_path_language(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('por', 'BR'))
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.pt-BR.srt'


def test_get_subtitle_path_language_undefined(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('und'))
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.srt'


def test_get_subtitle_path_hearing_impaired(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(
        Language('deu', 'CH', 'Latn'),
        language_type=LanguageType.HEARING_IMPAIRED,
        language_type_suffix=True,
    )
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.hi.de-CH-Latn.srt'


def test_get_subtitle_path_forced(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(
        Language('srp', None, 'Cyrl'),
        language_type=LanguageType.FORCED,
        language_type_suffix=True,
    )
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.forced.sr-Cyrl.srt'


def test_get_subtitle_path_alpha3(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('fra', 'CA'), language_format='alpha3')
    assert get_subtitle_path(video.name, suffix) == os.path.splitext(video.name)[0] + '.fra-CA.srt'


def test_get_subtitle_path_extension(movies):
    video = movies['man_of_steel']
    suffix = get_subtitle_suffix(Language('zho', 'CN'), language_type_suffix=True)
    assert get_subtitle_path(video.name, suffix, extension='.sub') == os.path.splitext(video.name)[0] + '.zh-CN.sub'


def test_fix_line_ending():
    content = b'Text\r\nwith\r\nweird\nline ending\r\ncharacters'
    assert fix_line_ending(content) == b'Text\nwith\nweird\nline ending\ncharacters'


# https://github.com/pannal/Sub-Zero.bundle/issues/646 replaced all Chinese character “不” with “上”
def test_fix_line_ending_chinese_characters():
    character = bytes('不', 'utf16')
    content = b''.join([character, b'\r\n', character, b'\n', character])
    expected = b''.join([character, b'\n', character, b'\n', character])
    assert fix_line_ending(content) == expected


def test_subtitle_valid_encoding():
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding='windows-1252',
    )
    assert subtitle.encoding == 'cp1252'


def test_subtitle_empty_encoding():
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding=None,
    )
    assert subtitle.encoding is None


def test_subtitle_invalid_encoding():
    subtitle = Subtitle(
        language=Language('deu'),
        hearing_impaired=False,
        page_link=None,
        encoding='rubbish',
    )
    assert subtitle.encoding is None


def test_subtitle_guess_encoding_utf8():
    subtitle = Subtitle(
        language=Language('zho'),
        forced=False,
        page_link=None,
        encoding=None,
    )
    subtitle.content = b'Something here'
    assert subtitle.forced is False
    assert subtitle.guess_encoding() == 'utf-8'
    assert subtitle.text == 'Something here'


# regression for #921
def test_subtitle_text_guess_encoding_none():
    content = b'\x00d\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff,\x00\x00\x00\x00d\x00d\x00\x00\x02s\x84\x8f\xa9'
    subtitle = Subtitle(
        language=Language('zho'),
        hearing_impaired=False,
        page_link=None,
        encoding=None,
    )
    subtitle.content = content

    assert subtitle.guess_encoding() is None
    assert not subtitle.is_valid()
    assert subtitle.text == ''


def test_subtitle_reencode() -> None:
    content = b'Uma palavra longa \xe9 melhor do que um p\xe3o curto'
    subtitle = Subtitle(
        language=Language('por'),
        encoding='latin1',
    )
    subtitle.content = content
    success = subtitle.reencode()
    assert success
    assert subtitle.content == b'Uma palavra longa \xc3\xa9 melhor do que um p\xc3\xa3o curto'


def test_subtitle_info(monkeypatch) -> None:
    subtitle = Subtitle(
        Language('eng'),
        'xv34e',
        forced=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nIn response to your honored\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_embedded_subtitle_info_hearing_impaired(monkeypatch) -> None:
    subtitle = EmbeddedSubtitle(
        Language('spa'),
        hearing_impaired=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn respuesta a su carta de\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)


def test_embedded_subtitle_info_forced(monkeypatch) -> None:
    subtitle = EmbeddedSubtitle(
        Language('fra'),
        forced=True,
    )
    text = '1\n00:00:20,000 --> 00:00:24,400\nEn réponse à votre honorée du tant\n\n'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True
    assert isinstance(subtitle.id, str)
    assert isinstance(subtitle.info, str)
