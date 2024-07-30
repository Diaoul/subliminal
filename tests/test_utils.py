import datetime
from typing import Any

from subliminal.utils import get_age, sanitize


def test_sanitize():
    assert sanitize("Marvel's Agents of S.H.I.E.L.D.") == 'marvels agents of s h i e l d'


def test_get_age(monkeypatch) -> None:
    NOW = datetime.datetime.now(datetime.timezone.utc)

    # mock file age
    def mock_modification_date(filepath: str, **kwargs: Any) -> float:
        return (NOW - datetime.timedelta(weeks=2)).timestamp()

    def mock_creation_date_later(*args: Any) -> float:
        return (NOW - datetime.timedelta(weeks=1)).timestamp()

    def mock_creation_date_sooner(*args: Any) -> float:
        return (NOW - datetime.timedelta(weeks=3)).timestamp()

    monkeypatch.setattr('subliminal.utils.modification_date', mock_modification_date)
    monkeypatch.setattr('subliminal.utils.creation_date', mock_creation_date_later)

    age = get_age(__file__, use_ctime=False, reference_date=NOW)
    assert age == datetime.timedelta(weeks=2)

    c_age = get_age(__file__, use_ctime=True, reference_date=NOW)
    assert c_age == datetime.timedelta(weeks=1)

    not_file_age = get_age('not-a-file.txt', reference_date=NOW)
    assert not_file_age == datetime.timedelta()

    # creation sooner
    monkeypatch.setattr('subliminal.utils.creation_date', mock_creation_date_sooner)

    c_age_2 = get_age(__file__, use_ctime=True, reference_date=NOW)
    assert c_age_2 == datetime.timedelta(weeks=2)
