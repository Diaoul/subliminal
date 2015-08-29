# -*- coding: utf-8 -*-
import os

from babelfish import Language

from subliminal.subtitle import (Subtitle, compute_score, fix_line_ending, get_subtitle_path, guess_matches,
                                 guess_properties)


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


def test_compute_score(episodes):
    video = episodes['bbt_s07e05']
    matches = {'series'}
    assert compute_score(matches, video) == video.scores['series']


def test_get_score_cap(movies):
    video = movies['man_of_steel']
    matches = {'format', 'video_codec', 'tvdb_id', 'title', 'imdb_id', 'audio_codec', 'year', 'resolution', 'season',
               'release_group', 'series', 'episode', 'hash'}
    assert compute_score(matches, video) == video.scores['hash']


def test_compute_score_episode_imdb_id(episodes):
    video = episodes['bbt_s07e05']
    matches = {'imdb_id', 'series', 'tvdb_id', 'season', 'episode', 'title', 'year'}
    assert compute_score(matches, video) == video.scores['imdb_id']


def test_compute_score_episode_tvdb_id(episodes):
    video = episodes['bbt_s07e05']
    matches = {'tvdb_id', 'series', 'year'}
    assert compute_score(matches, video) == video.scores['tvdb_id']


def test_compute_score_episode_title(episodes):
    video = episodes['bbt_s07e05']
    matches = {'title', 'season', 'episode'}
    assert compute_score(matches, video) == video.scores['title']


def test_compute_score_hash_hearing_impaired(episodes):
    video = episodes['bbt_s07e05']
    matches = {'hash', 'hearing_impaired'}
    assert compute_score(matches, video) == video.scores['hash'] + video.scores['hearing_impaired']


def test_get_subtitle_path(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, extension='.sub') == os.path.splitext(video.name)[0] + '.sub'


def test_get_subtitle_path_with_language(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, Language('por', 'BR')) == os.path.splitext(video.name)[0] + '.pt-BR.srt'


def test_get_subtitle_path_with_language_undefined(movies):
    video = movies['man_of_steel']
    assert get_subtitle_path(video.name, Language('und')) == os.path.splitext(video.name)[0] + '.srt'


def test_guess_matches_movie(movies):
    video = movies['man_of_steel']
    guess = {'title': video.title.upper(), 'year': video.year, 'releaseGroup': video.release_group.upper(),
             'screenSize': video.resolution, 'format': video.format.upper(), 'videoCodec': video.video_codec,
             'audioCodec': video.audio_codec}
    expected = {'title', 'year', 'release_group', 'resolution', 'format', 'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode(episodes):
    video = episodes['bbt_s07e05']
    guess = {'series': video.series, 'season': video.season, 'episodeNumber': video.episode, 'year': video.year,
             'title': video.title.upper(), 'releaseGroup': video.release_group.upper(), 'screenSize': video.resolution,
             'format': video.format.upper(), 'videoCodec': video.video_codec, 'audioCodec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'release_group', 'resolution', 'format', 'video_codec',
                'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_no_year(episodes):
    video = episodes['dallas_s01e03']
    guess = {'series': video.series, 'season': video.season, 'episodeNumber': video.episode}
    expected = {'series', 'season', 'episode', 'year'}
    assert guess_matches(video, guess) == expected


def test_guess_properties():
    string = '720p-BluRay'
    assert guess_properties(string) == {'format': 'BluRay', 'screenSize': '720p'}


def test_fix_line_ending():
    content = b'Text\r\nwith\rweird\nline ending\r\ncharacters'
    assert fix_line_ending(content) == b'Text\nwith\nweird\nline ending\ncharacters'
