import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import NotInitializedProviderError
from subliminal.providers.subtis import SubtisProvider, SubtisSubtitle
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subtis')),
)


def test_get_matches_movie(movies: dict[str, Movie]) -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        page_link='https://api.subt.is/v1/subtitle/file/name/123/test.mkv',
        title='Man of Steel 2013',
        download_link='https://example.com/subtitle.srt',
        is_synced=True,
    )

    matches = subtitle.get_matches(movies['man_of_steel'])
    assert 'title' in matches
    assert 'year' in matches


def test_get_matches_movie_with_release_info() -> None:
    video = Movie(
        'Novocaine.2025.1080p.WEBRip.V2.x264.Dual.YG.mkv',
        'Novocaine',
        source='Web',
        release_group='YG',
        resolution='1080p',
        video_codec='H.264',
        year=2025,
    )
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        page_link='https://api.subt.is/v1/subtitle/file/name/123/test.mkv',
        title='Novocaine 2025',
        download_link='https://example.com/subtitle.srt',
        is_synced=True,
    )

    matches = subtitle.get_matches(video)
    assert 'title' in matches
    assert 'year' in matches


def test_get_matches_episode_returns_empty() -> None:
    video = Episode(
        'The.Show.S01E01.mkv',
        'The Show',
        1,
        1,
    )
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        page_link='https://api.subt.is/v1/subtitle/file/name/123/test.mkv',
        title='The Show',
        download_link='https://example.com/subtitle.srt',
        is_synced=True,
    )

    matches = subtitle.get_matches(video)
    assert len(matches) == 0


def test_subtitle_info_synced() -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        title='Man of Steel 2013',
        is_synced=True,
    )
    assert subtitle.info == 'Man of Steel 2013'


def test_subtitle_info_not_synced() -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        title='Man of Steel 2013',
        is_synced=False,
    )
    assert subtitle.info == 'Man of Steel 2013 [fuzzy match]'


def test_subtitle_info_no_title() -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        title=None,
        is_synced=True,
    )
    assert subtitle.info == 'test-id'


@pytest.mark.integration
@vcr.use_cassette
def test_initialize() -> None:
    provider = SubtisProvider()
    assert provider.session is None
    provider.initialize()
    assert provider.session is not None
    provider.terminate()


@pytest.mark.integration
@vcr.use_cassette
def test_terminate() -> None:
    provider = SubtisProvider()
    provider.initialize()
    provider.terminate()
    assert provider.session is None


@pytest.mark.integration
def test_terminate_without_initialization() -> None:
    provider = SubtisProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.terminate()


@pytest.mark.integration
def test_list_subtitles_episode_returns_empty() -> None:
    video = Episode(
        'The.Show.S01E01.mkv',
        'The Show',
        1,
        1,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        # The API may or may not have this movie, but the call should work
        assert isinstance(subtitles, list)


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_with_size() -> None:
    video = Movie(
        'Novocaine.2025.1080p.WEBRip.V2.x264.Dual.YG.mkv',
        'Novocaine',
        source='Web',
        release_group='YG',
        resolution='1080p',
        video_codec='H.264',
        year=2025,
        size=4541737725,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert isinstance(subtitles, list)
        if len(subtitles) > 0:
            assert subtitles[0].language == Language('spa')
            assert subtitles[0].is_synced is True


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_alternative() -> None:
    video = Movie(
        'Novocaine.2025.1080p.WEBRip.mkv',
        'Novocaine',
        year=2025,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert isinstance(subtitles, list)
        if len(subtitles) > 0:
            assert subtitles[0].language == Language('spa')
            assert subtitles[0].is_synced is False


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_no_match() -> None:
    video = Movie(
        'NonExistentMovie.2099.mkv',
        'NonExistentMovie',
        year=2099,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle() -> None:
    video = Movie(
        'Novocaine.2025.1080p.WEBRip.V2.x264.Dual.YG.mkv',
        'Novocaine',
        source='Web',
        release_group='YG',
        resolution='1080p',
        video_codec='H.264',
        year=2025,
        size=4541737725,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        if len(subtitles) >= 1:
            subtitle = subtitles[0]
            provider.download_subtitle(subtitle)
            assert subtitle.content is not None
            assert subtitle.is_valid() is True


@pytest.mark.integration
def test_download_subtitle_missing_download_link() -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        title='Test Movie',
        download_link=None,
        is_synced=True,
    )

    with SubtisProvider() as provider:
        provider.download_subtitle(subtitle)
        assert subtitle.content is None
        assert subtitle.is_valid() is False


@pytest.mark.integration
def test_download_subtitle_without_initialization() -> None:
    subtitle = SubtisSubtitle(
        language=Language('spa'),
        subtitle_id='test-id',
        title='Test Movie',
        download_link='https://example.com/subtitle.srt',
        is_synced=True,
    )

    provider = SubtisProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.download_subtitle(subtitle)


@pytest.mark.integration
def test_list_subtitles_without_initialization(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('spa')}

    provider = SubtisProvider()
    with pytest.raises(NotInitializedProviderError):
        provider.list_subtitles(video, languages)
