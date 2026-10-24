from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

from subliminal.archives import is_supported_archive, scan_archive, scan_archive_rar
from subliminal.core import scan_video_or_archive, scan_videos
from subliminal.exceptions import ArchiveError

unix_platform = pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='only on linux platform',
)

# Core test
pytestmark = [pytest.mark.core, unix_platform]


def test_is_supported_archive(rar: dict[str, str], mkv: dict[str, str]) -> None:
    assert is_supported_archive(rar['simple'])
    assert not is_supported_archive(mkv['test1'])


def test_scan_archive_with_one_video(rar: dict[str, str], mkv: dict[str, str]) -> None:
    if 'video' not in rar:
        return
    rar_file = rar['video']
    actual = scan_archive(rar_file)

    expected = os.fspath(Path(rar_file).parent / Path(mkv['test1']).name)
    assert actual.name == expected


def test_scan_archive_with_multiple_videos(rar: dict[str, str], mkv: dict[str, str]) -> None:
    if 'videos' not in rar:
        return
    rar_file = rar['videos']
    actual = scan_archive(rar_file)

    expected = os.fspath(Path(rar_file).parent / Path(mkv['test5']).name)
    assert actual.name == expected


def test_scan_archive_with_no_video(rar: dict[str, str]) -> None:
    with pytest.raises(ArchiveError, match='No video in archive'):
        scan_archive(rar['simple'])


def test_scan_bad_archive(mkv: dict[str, str]) -> None:
    with pytest.raises(ArchiveError, match=re.escape("'.mkv' is not a valid archive")):
        scan_archive(mkv['test1'])


def test_scan_rar_not_a_file(mkv: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=re.escape("Path does not exist: 'not_a_file.txt'")):
        scan_archive_rar('not_a_file.txt')


def test_scan_rar_bad_archive(mkv: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=re.escape("'.mkv' is not a valid archive")):
        scan_archive_rar(mkv['test1'])


def test_scan_password_protected_archive(rar: dict[str, str]) -> None:
    with pytest.raises(ArchiveError, match='Rar requires a password'):
        scan_archive(rar['pwd-protected'])


def test_scan_archive_error(
    rar: dict[str, str],
) -> None:
    if 'pwd-protected' not in rar:
        return
    path = rar['pwd-protected']
    with pytest.raises(ArchiveError):
        scan_archive(path)

    with pytest.raises(ValueError, match='Error scanning archive'):
        scan_video_or_archive(path)


def test_scan_videos_error(
    rar: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    if 'pwd-protected' not in rar:
        return
    folder = Path(rar['pwd-protected']).parent
    # Test return without error
    scan_videos(folder)

    # But error was logged
    error_records = [record for record in caplog.records if record.levelname == 'ERROR']
    assert len(error_records) > 0
    assert 'Error scanning archive' in caplog.text
