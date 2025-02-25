from pathlib import Path

from subliminal.refiners.hash import hash_opensubtitles


def test_hash_opensubtitles(mkv: dict[str, str]) -> None:
    assert hash_opensubtitles(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_opensubtitles_too_small(tmp_path: Path) -> None:
    path = tmp_path / 'test_too_small.mkv'
    path.touch()
    assert hash_opensubtitles(str(path)) is None
