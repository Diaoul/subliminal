# -*- coding: utf-8 -*-
import os

from babelfish import Language

from subliminal.subtitle import Subtitle, fix_line_ending, get_subtitle_path, guess_matches


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


def test_guess_matches_movie(movies):
    video = movies['man_of_steel']
    guess = {'title': video.title.upper(), 'year': video.year, 'release_group': video.release_group.upper(),
             'screen_size': video.resolution, 'format': video.format.upper(), 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'title', 'year', 'release_group', 'resolution', 'format', 'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode(episodes):
    video = episodes['bbt_s07e05']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': video.release_group.upper(),
             'screen_size': video.resolution, 'format': video.format.upper(), 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'release_group', 'resolution', 'format', 'video_codec',
                'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_equivalent_release_group(episodes):
    video = episodes['bbt_s07e05']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': 'LOL',
             'screen_size': video.resolution, 'format': video.format.upper(), 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'release_group', 'resolution', 'format', 'video_codec',
                'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_no_year(episodes):
    video = episodes['dallas_s01e03']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode}
    expected = {'series', 'season', 'episode', 'year'}
    assert guess_matches(video, guess) == expected


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


def test_guess_multiple_formats(movies):
    video = movies['inferno']
    guess = {'title': video.title.upper(), 'year': video.year, 'release_group': video.release_group.upper(),
             'screen_size': video.resolution, 'format': video.format, 'video_codec': video.video_codec}
    expected = {'title', 'year', 'release_group', 'resolution', 'video_codec'}
    # Assert `format` is not a match
    assert guess_matches(video, guess) == expected
