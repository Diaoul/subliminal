from pathlib import Path

from babelfish import Language  # type: ignore[import-untyped]

from subliminal.extensions import get_default_providers
from subliminal.refiners.hash import hash_opensubtitles, refine
from subliminal.video import Movie


def test_hash_opensubtitles(mkv: dict[str, str]) -> None:
    assert hash_opensubtitles(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_opensubtitles_too_small(tmp_path: Path) -> None:
    path = tmp_path / 'test_too_small.mkv'
    path.touch()
    assert hash_opensubtitles(str(path)) is None


def test_refine_too_small(mkv: dict[str, str]) -> None:
    path = mkv['test1']
    video = Movie.fromguess(path, {'type': 'movie', 'title': 'Titanic'})

    # video too small
    assert video.size is None or video.size < 10485760
    refine(video, providers=get_default_providers())
    assert len(video.hashes) == 0


def test_refine(mkv: dict[str, str]) -> None:
    path = mkv['test1']
    video = Movie.fromguess(path, {'type': 'movie', 'title': 'Titanic'})

    # hide true size
    video.size = 10485761
    refine(video, providers=get_default_providers())

    expected = {
        'opensubtitlescom': '40b44a7096b71ec3',
        # 'bsplayer': '40b44a7096b71ec3',
        'napiprojekt': '9884a2b66dcb2965d0f45ce84e37b60c',
        'opensubtitles': '40b44a7096b71ec3',
    }
    assert video.hashes == expected


def test_refine_no_language(mkv: dict[str, str]) -> None:
    path = mkv['test1']
    video = Movie.fromguess(path, {'type': 'movie', 'title': 'Titanic'})

    # Napiprojekt only supports polish
    languages = {Language('ita')}

    # hide true size
    video.size = 10485761
    refine(video, providers=['napiprojekt'], languages=languages)

    assert len(video.hashes) == 0
