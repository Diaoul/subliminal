# -*- coding: utf-8 -*-
from datetime import timedelta
import io
import os
from pkg_resources import EntryPoint, iter_entry_points

from babelfish import Language
import pytest
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock
from vcr import VCR

from subliminal import (ProviderManager, ProviderPool, check_video, download_best_subtitles, download_subtitles,
                        list_subtitles, provider_manager, save_subtitles)
from subliminal.providers.addic7ed import Addic7edSubtitle
from subliminal.providers.thesubdb import TheSubDBSubtitle
from subliminal.providers.tvsubtitles import TVsubtitlesSubtitle
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'api'))


@pytest.fixture
def mock_providers(monkeypatch):
    for provider in provider_manager:
        monkeypatch.setattr(provider.plugin, 'initialize', Mock())
        monkeypatch.setattr(provider.plugin, 'list_subtitles', Mock(return_value=[provider.name]))
        monkeypatch.setattr(provider.plugin, 'download_subtitle', Mock())
        monkeypatch.setattr(provider.plugin, 'terminate', Mock())


def test_provider_manager_internal_providers():
    manager = ProviderManager()
    setup_names = {ep.name for ep in iter_entry_points(manager.namespace)}
    internal_names = {EntryPoint.parse(iep).name for iep in manager.internal_providers}
    assert internal_names == setup_names


def test_provider_manager_register():
    manager = ProviderManager()
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert 'de7cidda' in manager.names()


def test_provider_manager_unregister():
    manager = ProviderManager()
    old_names = manager.names()
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    manager.unregister('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert set(old_names) == set(manager.names())


def test_provider_pool_get_keyerror():
    pool = ProviderPool()
    with pytest.raises(KeyError):
        pool['de7cidda']


def test_provider_pool_del_keyerror():
    pool = ProviderPool()
    with pytest.raises(KeyError):
        del pool['addic7ed']


def test_provider_pool_iter(mock_providers):
    pool = ProviderPool()
    assert len(list(pool)) == 0
    pool['tvsubtitles']
    assert len(list(pool)) == 1


def test_check_video_languages(movies):
    video = movies['man_of_steel']
    languages = {Language('fra'), Language('eng')}
    assert check_video(video, languages=languages)
    video.subtitle_languages = languages
    assert not check_video(video, languages=languages)


def test_check_video_age(movies, monkeypatch):
    video = movies['man_of_steel']
    monkeypatch.setattr('subliminal.video.Video.age', timedelta(weeks=2))
    assert check_video(video, age=timedelta(weeks=3))
    assert not check_video(video, age=timedelta(weeks=1))


def test_check_video_undefined(movies):
    video = movies['man_of_steel']
    assert check_video(video, undefined=False)
    assert check_video(video, undefined=True)
    video.subtitle_languages = {Language('und')}
    assert check_video(video, undefined=False)
    assert not check_video(video, undefined=True)


def test_list_subtitles_movie(movies, mock_providers):
    video = movies['man_of_steel']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    assert not provider_manager['addic7ed'].plugin.list_subtitles.called
    assert provider_manager['opensubtitles'].plugin.list_subtitles.called
    assert provider_manager['podnapisi'].plugin.list_subtitles.called
    assert not provider_manager['subscenter'].plugin.list_subtitles.called
    assert provider_manager['thesubdb'].plugin.list_subtitles.called
    assert not provider_manager['tvsubtitles'].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[movies['man_of_steel']]) == ['opensubtitles', 'podnapisi', 'thesubdb']


def test_list_subtitles_episode(episodes, mock_providers):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    assert provider_manager['addic7ed'].plugin.list_subtitles.called
    assert provider_manager['opensubtitles'].plugin.list_subtitles.called
    assert provider_manager['podnapisi'].plugin.list_subtitles.called
    assert provider_manager['subscenter'].plugin.list_subtitles.called
    assert provider_manager['thesubdb'].plugin.list_subtitles.called
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['addic7ed', 'opensubtitles', 'podnapisi', 'subscenter',
                                                         'thesubdb', 'tvsubtitles']


def test_list_subtitles_providers(episodes, mock_providers):
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages, providers=['addic7ed'])

    # test providers
    assert provider_manager['addic7ed'].plugin.list_subtitles.called
    assert not provider_manager['opensubtitles'].plugin.list_subtitles.called
    assert not provider_manager['podnapisi'].plugin.list_subtitles.called
    assert not provider_manager['subscenter'].plugin.list_subtitles.called
    assert not provider_manager['thesubdb'].plugin.list_subtitles.called
    assert not provider_manager['tvsubtitles'].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['addic7ed']


def test_list_subtitles_episode_no_hash(episodes, mock_providers):
    video = episodes['dallas_s01e03']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    assert provider_manager['addic7ed'].plugin.list_subtitles.called
    assert provider_manager['opensubtitles'].plugin.list_subtitles.called
    assert provider_manager['podnapisi'].plugin.list_subtitles.called
    assert provider_manager['subscenter'].plugin.list_subtitles.called
    assert not provider_manager['thesubdb'].plugin.list_subtitles.called
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['dallas_s01e03']]) == ['addic7ed', 'opensubtitles', 'podnapisi', 'subscenter',
                                                            'tvsubtitles']


def test_list_subtitles_no_language(episodes, mock_providers):
    video = episodes['dallas_s01e03']
    languages = {Language('eng')}
    video.subtitle_languages = languages

    subtitles = list_subtitles({video}, languages)

    # test providers
    assert not provider_manager['addic7ed'].plugin.list_subtitles.called
    assert not provider_manager['opensubtitles'].plugin.list_subtitles.called
    assert not provider_manager['podnapisi'].plugin.list_subtitles.called
    assert not provider_manager['subscenter'].plugin.list_subtitles.called
    assert not provider_manager['thesubdb'].plugin.list_subtitles.called
    assert not provider_manager['tvsubtitles'].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 0


def test_download_subtitles(mock_providers):
    subtitles = [
        Addic7edSubtitle(Language('eng'), True, None, 'The Big Bang Theory', 7, 5, 'The Workplace Proximity', 2007,
                         'DIMENSION', None),
        TheSubDBSubtitle(Language('eng'), 'ad32876133355929d814457537e12dc2'),
        TVsubtitlesSubtitle(Language('por'), None, 261077, 'Game of Thrones', 3, 10, None, '1080p.BluRay', 'DEMAND')
    ]

    download_subtitles(subtitles)

    # test providers
    assert provider_manager['addic7ed'].plugin.download_subtitle.called
    assert not provider_manager['opensubtitles'].plugin.download_subtitle.called
    assert not provider_manager['podnapisi'].plugin.download_subtitle.called
    assert provider_manager['thesubdb'].plugin.download_subtitle.called
    assert provider_manager['tvsubtitles'].plugin.download_subtitle.called
    assert not provider_manager['subscenter'].plugin.download_subtitle.called


@pytest.mark.integration
@vcr.use_cassette
def test_download_best_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('nld'), Language('por', 'BR')}
    providers = ['addic7ed', 'thesubdb']
    expected_subtitles = {('addic7ed', 'updated/17/80254/11'), ('thesubdb', '9dbbfb7ba81c9a6237237dae8589fccc-pt-BR')}

    subtitles = download_best_subtitles({video}, languages, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 2
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_download_best_subtitles_min_score(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    providers = ['addic7ed']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0


def test_download_best_subtitles_no_language(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    video.subtitle_languages = languages
    providers = ['addic7ed']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 0


def test_download_best_subtitles_undefined(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('und')}
    video.subtitle_languages = languages
    providers = ['addic7ed']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], only_one=True,
                                        providers=providers)

    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette('test_download_best_subtitles')
def test_download_best_subtitles_only_one(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('nld'), Language('por', 'BR')}
    providers = ['addic7ed', 'thesubdb']
    expected_subtitles = {('thesubdb', '9dbbfb7ba81c9a6237237dae8589fccc-pt-BR')}

    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


def test_save_subtitles(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(movies['man_of_steel'].name)
    subtitle_no_content = Subtitle(Language('eng'))
    subtitle = Subtitle(Language('fra'))
    subtitle.content = b'Some content'
    subtitle_other = Subtitle(Language('fra'))
    subtitle_other.content = b'Some other content'
    subtitle_pt_br = Subtitle(Language('por', 'BR'))
    subtitle_pt_br.content = b'Some brazilian content'
    subtitles = [subtitle_no_content, subtitle, subtitle_other, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles)

    # subtitle without content is skipped
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.en.srt')
    assert not os.path.exists(path)

    # first subtitle with language is saved
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.fr.srt')
    assert os.path.exists(path)
    assert io.open(path, 'rb').read() == b'Some content'

    # ietf language in path
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.pt-BR.srt')
    assert os.path.exists(path)
    assert io.open(path, 'rb').read() == b'Some brazilian content'


def test_save_subtitles_single_directory_encoding(movies, tmpdir):
    subtitle = Subtitle(Language('jpn'))
    subtitle.content = u'ハローワールド'.encode('shift-jis')
    subtitle_pt_br = Subtitle(Language('por', 'BR'))
    subtitle_pt_br.content = b'Some brazilian content'
    subtitles = [subtitle, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles, single=True, directory=str(tmpdir), encoding='utf-8')

    # first subtitle only and correctly encoded
    path = os.path.join(str(tmpdir), os.path.splitext(os.path.split(movies['man_of_steel'].name)[1])[0] + '.srt')
    assert os.path.exists(path)
    assert io.open(path, encoding='utf-8').read() == u'ハローワールド'
