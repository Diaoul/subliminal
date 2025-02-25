from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from knowit.units import units  # type: ignore[import-untyped]

from subliminal.core import scan_video
from subliminal.refiners.metadata import (
    get_float,
    get_subtitle_format,
    loaded_providers,
    refine,
)

providers = ['mediainfo', 'ffmpeg', 'mkvmerge', 'enzyme']


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, None),
        (1, 1.0),
        (2, 2.0),
        ('3.14', 3.14),
        (timedelta(hours=1, minutes=60, seconds=60), 7260.0),
        (24 * units.FPS, 24.0),
    ],
)
def test_get_float(value: Any, expected: float | None) -> None:
    ret = get_float(value)
    assert ret is None or isinstance(ret, float)
    assert ret == expected


def test_get_float_error() -> None:
    with pytest.raises(TypeError):
        get_float((1.0,))


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, None),
        ('ass', 'ass'),
        ('ssa', 'ssa'),
        ('subrip', 'srt'),
        ('pgs', 'pgs'),
    ],
)
def test_get_subtitle_format(value: str | None, expected: str | None) -> None:
    """Convert str subrip -> srt."""
    subtitle_format = get_subtitle_format(value)
    assert subtitle_format == expected


@pytest.mark.parametrize('provider', providers)
def test_refine_video_metadata(mkv: dict[str, Any], provider: str) -> None:
    # Skip test if provider is not installed
    if not loaded_providers().get(provider, False):
        pytest.skip(f'uninstalled provider {provider}')

    # Scan video
    scanned_video = scan_video(mkv['test5'])
    assert scanned_video.name == mkv['test5']
    assert scanned_video.resolution is None
    assert scanned_video.size == 31762747

    # Refine with file metadata
    refine(scanned_video, embedded_subtitles=True, metadata_provider=provider)
    assert scanned_video.resolution is None
    assert scanned_video.duration == 46.665
    assert scanned_video.video_codec == 'H.264'
    assert scanned_video.audio_codec == 'AAC'

    # Enzyme has limited functionalities
    if provider == 'enzyme':
        assert scanned_video.subtitle_languages == {
            # Language('eng'),  # bug with enzyme
            Language('spa'),
            Language('deu'),
            Language('jpn'),
            Language('und'),
            Language('ita'),
            Language('fra'),
            Language('hun'),
        }

    # other providers
    else:
        if provider != 'mkvmerge':
            assert scanned_video.frame_rate == 24

        assert scanned_video.subtitle_languages == {
            Language('eng'),
            Language('spa'),
            Language('deu'),
            Language('jpn'),
            Language('und'),
            Language('ita'),
            Language('fra'),
            Language('hun'),
        }
        for subtitle in scanned_video.subtitles:
            assert subtitle.subtitle_format == 'srt'


def test_refine_video_metadata_no_provider(mkv: dict[str, Any]) -> None:
    scanned_video = scan_video(mkv['test5'])
    refine(scanned_video, embedded_subtitles=True)

    assert scanned_video.duration == 46.665
    # cannot put 8, because if enzyme is used it finds only 7
    assert len(scanned_video.subtitle_languages) >= 7


def test_refine_video_metadata_wrong_provider(mkv: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    scanned_video = scan_video(mkv['test5'])
    with caplog.at_level(logging.WARNING):
        refine(scanned_video, embedded_subtitles=True, metadata_provider='not-a-provider')

    assert "metadata_provider='not-a-provider' is not a valid argument" in caplog.text


def test_refine_video_metadata_no_embedded_subtitles(mkv: dict[str, Any]) -> None:
    scanned_video = scan_video(mkv['test5'])
    refine(scanned_video, embedded_subtitles=False)

    assert scanned_video.duration == 46.665
    assert len(scanned_video.subtitle_languages) == 0


def test_refine_no_subtitle_track(mkv: dict[str, Any]) -> None:
    """Also tests resolution 480p."""
    scanned_video = scan_video(mkv['test1'])
    refine(scanned_video, embedded_subtitles=True)

    assert scanned_video.duration == 87.336
    assert scanned_video.resolution == '480p'
    assert len(scanned_video.subtitle_languages) == 0
