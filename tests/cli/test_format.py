from __future__ import annotations

import pytest

from subliminal.cli.commands._format import format_provider_errors

# Core test
pytestmark = pytest.mark.core


@pytest.mark.parametrize(
    ('failed', 'discarded', 'video_count', 'expected'),
    [
        # with one video, both kinds of error give the same message
        ({'podnapisi'}, set(), 1, 'These providers had an error and found no subtitles: podnapisi.'),
        ({'podnapisi'}, {'podnapisi'}, 1, 'These providers had an error and found no subtitles: podnapisi.'),
        (
            {'gestdown', 'podnapisi', 'tvsubtitles'},
            {'gestdown'},
            1,
            'These providers had an error and found no subtitles: gestdown, podnapisi, tvsubtitles.',
        ),
        # with more videos, each kind gets its own sentence
        (
            {'gestdown'},
            {'gestdown'},
            3,
            'These providers had an error and were skipped for the rest of the download: gestdown. '
            'Some subtitles can be missing.',
        ),
        (
            {'podnapisi', 'tvsubtitles'},
            set(),
            3,
            'These providers had an error on some videos: podnapisi, tvsubtitles. Some subtitles can be missing.',
        ),
        (
            {'gestdown', 'podnapisi', 'tvsubtitles'},
            {'gestdown'},
            3,
            'These providers had an error and were skipped for the rest of the download: gestdown. '
            'These providers had an error on some videos: podnapisi, tvsubtitles. '
            'Some subtitles can be missing.',
        ),
    ],
)
def test_format_provider_errors(failed: set[str], discarded: set[str], video_count: int, expected: str) -> None:
    assert format_provider_errors(failed, discarded, video_count=video_count) == expected
