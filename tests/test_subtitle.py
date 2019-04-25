# -*- coding: utf-8 -*-
import os

import six
from babelfish import Language

from subliminal.subtitle import Subtitle, fix_line_ending, get_subtitle_path


def test_subtitle_text():
    subtitle = Subtitle(Language('eng'))
    subtitle.content = b'Some ascii text'
    assert subtitle.text == 'Some ascii text'


def test_subtitle_text_no_content():
    subtitle = Subtitle(Language('eng'))
    assert subtitle.text is None


def test_subtitle_is_valid_no_content():
    subtitle = Subtitle(Language('fra'))
    assert subtitle.is_valid() is False


def test_subtitle_is_valid_valid(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (u'1\n'
            u'00:00:20,000 --> 00:00:24,400\n'
            u'En réponse à l\'augmentation de la criminalité\n'
            u'dans certains quartiers,\n')
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


def test_subtitle_is_valid_invalid(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (u'1\n'
            u'00:00:20,000 --> 00:00:24,400\n'
            u'En réponse à l\'augmentation de la criminalité\n'
            u'dans certains quartiers,\n\n')
    text += u'This line shouldn\'t be here'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is False


def test_subtitle_is_valid_valid_begin(monkeypatch):
    subtitle = Subtitle(Language('fra'))
    text = (u'1\n'
            u'00:00:20,000 --> 00:00:24,400\n'
            u'En réponse à l\'augmentation de la criminalité\n'
            u'dans certains quartiers,\n\n')*20
    text += u'This line shouldn\'t be here'
    monkeypatch.setattr(Subtitle, 'text', text)
    assert subtitle.is_valid() is True


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
    content = b'Text\r\nwith\rweird\nline ending\r\ncharacters'
    assert fix_line_ending(content) == b'Text\nwith\nweird\nline ending\ncharacters'


def test_subtitle_valid_encoding():
    subtitle = Subtitle(Language('deu'), False, None, 'windows-1252')
    assert subtitle.encoding == 'cp1252'


def test_subtitle_empty_encoding():
    subtitle = Subtitle(Language('deu'), False, None, None)
    assert subtitle.encoding is None


def test_subtitle_invalid_encoding():
    subtitle = Subtitle(Language('deu'), False, None, 'rubbish')
    assert subtitle.encoding is None


def test_subtitle_guess_encoding_utf8():
    subtitle = Subtitle(Language('zho'), False, None, None)
    subtitle.content = b'Something here'
    assert subtitle.guess_encoding() == 'utf-8'
    assert isinstance(subtitle.text, six.text_type)


# regression for #921
def test_subtitle_text_guess_encoding_none():
    content = b'\x00d\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff,\x00\x00\x00\x00d\x00d\x00\x00\x02s\x84\x8f\xa9'
    subtitle = Subtitle(Language('zho'), False, None, None)
    subtitle.content = content

    assert subtitle.guess_encoding() is None
    assert not subtitle.is_valid()
    assert not isinstance(subtitle.text, six.text_type)
