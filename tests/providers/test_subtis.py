import os
from unittest.mock import MagicMock, patch

import pytest
from babelfish import Language
from vcr import VCR

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
    assert 'release_group' in matches
    assert 'source' in matches
    assert 'resolution' in matches
    assert 'video_codec' in matches


def test_get_matches_movie_not_synced_no_release_matches() -> None:
    """Non-synced subtitles should not get release-level matches."""
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
        page_link='https://api.subt.is/v1/subtitle/file/alternative/test.mkv',
        title='Novocaine 2025',
        download_link='https://example.com/subtitle.srt',
        is_synced=False,
    )

    matches = subtitle.get_matches(video)
    assert 'title' in matches
    assert 'year' in matches
    assert 'release_group' not in matches
    assert 'source' not in matches
    assert 'resolution' not in matches
    assert 'video_codec' not in matches


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
        assert isinstance(subtitles, list)


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_hash(movies: dict[str, Movie], monkeypatch: pytest.MonkeyPatch) -> None:
    """Test searching by hash (Step 1 of cascade)."""

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as f:
        video_path = f.name

    try:
        video = Movie(
            video_path,
            'Novocaine',
            year=2025,
            size=123456789,
        )
        languages = {Language('spa')}

        def mock_compute_hash(self: SubtisProvider, path: str) -> str | None:
            return '1234567890abcdef'

        monkeypatch.setattr(SubtisProvider, '_compute_opensubtitles_hash', mock_compute_hash)

        with SubtisProvider() as provider:
            subtitles = provider.list_subtitles(video, languages)
            assert isinstance(subtitles, list)
            if len(subtitles) > 0:
                assert subtitles[0].language == Language('spa')
                assert subtitles[0].is_synced is True
                assert subtitles[0].page_link is not None
                assert '/file/hash/' in subtitles[0].page_link
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_with_size() -> None:
    """Test searching by size/bytes (Step 2 of cascade).

    This test uses a non-existent file path, so hash search (Step 1) is skipped.
    It has a size, so it triggers the bytes search.
    """
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
            assert subtitles[0].page_link is not None
            assert '/file/bytes/' in subtitles[0].page_link


@pytest.mark.integration
def test_list_subtitles_filename() -> None:
    """Test searching by filename (Step 3 of cascade).

    This test uses a non-existent file path (skips Step 1 Hash).
    It has NO size (skips Step 2 Bytes).
    It forces the filename search.

    We mock the API response here because obtaining an EXACT filename match
    guaranteed to exist in the live API is difficult and flaky.
    """
    video = Movie(
        'Mocked.Movie.2025.1080p.mkv',
        'Mocked Movie',
        year=2025,
    )
    languages = {Language('spa')}

    with SubtisProvider() as provider:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subtitle': {'subtitle_link': 'http://mock.com/dl'},
            'title': {'title_name': 'Mocked Movie'},
        }

        with patch.object(provider.session, 'get', return_value=mock_response) as mock_get:
            subtitles = provider.list_subtitles(video, languages)

            assert isinstance(subtitles, list)
            assert len(subtitles) > 0
            assert subtitles[0].language == Language('spa')
            assert subtitles[0].is_synced is True

            args, _ = mock_get.call_args
            assert '/find/file/name/' in args[0]
            assert 'Mocked.Movie.2025.1080p.mkv' in args[0]


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_alternative() -> None:
    """Test searching by alternative/fuzzy (Step 4 of cascade).

    This test relies on previous steps failing to find a match.
    """
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
