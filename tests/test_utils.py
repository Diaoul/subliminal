from subliminal.utils import sanitize


def test_sanitize():
    assert sanitize("Marvel's Agents of S.H.I.E.L.D.") == 'marvels agents of s h i e l d'
