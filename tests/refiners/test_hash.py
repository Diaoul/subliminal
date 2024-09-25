from subliminal.refiners.hash import hash_opensubtitles


def test_hash_opensubtitles(mkv):
    assert hash_opensubtitles(mkv['test1']) == '40b44a7096b71ec3'


def test_hash_opensubtitles_too_small(tmpdir):
    path = tmpdir.ensure('test_too_small.mkv')
    assert hash_opensubtitles(str(path)) is None
