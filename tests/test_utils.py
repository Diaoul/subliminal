from datetime import timedelta

from subliminal.utils import creation_date, get_age, modification_date, sanitize


def test_sanitize():
    assert sanitize("Marvel's Agents of S.H.I.E.L.D.") == 'marvels agents of s h i e l d'


def test_get_age() -> None:
    age = get_age(__file__)
    assert age > timedelta()

    c_age = get_age(__file__, use_ctime=True)
    assert c_age > timedelta()

    not_file_age = get_age('not-a-file.txt')
    assert not_file_age == timedelta()

    creation_or_modification = creation_date(__file__)
    modification = modification_date(__file__)
    assert creation_or_modification >= modification
