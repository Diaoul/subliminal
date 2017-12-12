# -*- coding: utf-8 -*-
from babelfish import Language
import os
import pytest
from subliminal.providers.argenteam import ArgenteamSubtitle, ArgenteamProvider
from vcr import VCR

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'argenteam'))


def test_get_matches_episode(episodes):
    subtitle = ArgenteamSubtitle(Language.fromalpha2('es'), None, 'Game of Thrones', 3, 10, 'EVOLVE', '720p')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'resolution', 'series', 'season', 'episode'}


def test_get_matches_no_match(episodes):
    subtitle = ArgenteamSubtitle(Language.fromalpha2('es'),
                                 None,
                                 'Marvels Agents Of S.H.I.E.L.D.',
                                 2, 6, 'KILLERS', '1080p')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language.fromalpha2('es')}
    with ArgenteamProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
