from six import text_type as str

from subliminal.utils import hash_opensubtitles, hash_thesubdb, sanitize


def test_hash_opensubtitles(mkv):
    assert hash_opensubtitles(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_opensubtitles_too_small(tmpdir):
    path = tmpdir.ensure('test_too_small.mkv')
    assert hash_opensubtitles(str(path)) is None


def test_hash_thesubdb(mkv):
    assert hash_thesubdb(mkv['test1']) == '054e667e93e254f8fa9f9e8e6d4e73ff'


def test_hash_thesubdb_too_small(tmpdir):
    path = tmpdir.ensure('test_too_small.mkv')
    assert hash_thesubdb(str(path)) is None


def test_sanitize():
    assert sanitize('Marvel\'s Agents of S.H.I.E.L.D.') == 'marvels agents of s h i e l d'
