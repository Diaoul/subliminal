import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from subliminal.subtitle import Subtitle, fix_line_ending, get_subtitle_path


def test_subtitle_text():
    subtitle = Subtitle(Language('eng'))
    subtitle.content = b'Some ascii text'
    assert subtitle.text == 'Some ascii text'


def test_subtitle_text_no_content():
    subtitle = Subtitle(Language('eng'))
    assert subtitle.text == ''


def test_subtitle_is_valid_no_content():
    subtitle = Subtitle(Language('fra'))
    assert subtitle.is_valid() is False


def test_subtitle_is_valid_valid(monkeypatch):
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


@pytest.mark.xfail()
def test_subtitle_is_valid_invalid(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (
        '1\n'
        '00:00:20,000 --> 00:00:24,400\n'
        "En réponse à l'augmentation de la criminalité\n"
        'dans certains quartiers,\n\n'
    )
    text += "This line shouldn't be here"
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is False


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


def test_get_subtitle_path(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, extension='.sub') == os.path.splitext(video.name)[0] + '.sub'


def test_get_subtitle_path_language(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, Language('por', 'BR')) == os.path.splitext(video.name)[0] + '.pt-BR.srt'


def test_get_subtitle_path_language_undefined(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, Language('und')) == os.path.splitext(video.name)[0] + '.srt'


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
        hearing_impaired=False,
        page_link=None,
        encoding=None,
    )
    subtitle.content = b'Something here'
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
