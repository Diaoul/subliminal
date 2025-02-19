# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from subliminal.archives import is_supported_archive, scan_archive, scan_archive_rar
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
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(rar['simple'])
    assert excinfo.value.args == ('No video in archive',)


def test_scan_bad_archive(mkv: dict[str, str]) -> None:
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(mkv['test1'])
    assert excinfo.value.args == ("'.mkv' is not a valid archive",)


def test_scan_rar_not_a_file(mkv: dict[str, str]) -> None:
    with pytest.raises(ValueError) as excinfo:
        scan_archive_rar('not_a_file.txt')
    assert excinfo.value.args == ("Path does not exist: 'not_a_file.txt'",)


def test_scan_rar_bad_archive(mkv: dict[str, str]) -> None:
    with pytest.raises(ValueError) as excinfo:
        scan_archive_rar(mkv['test1'])
    assert excinfo.value.args == ("'.mkv' is not a valid archive",)


def test_scan_password_protected_archive(rar: dict[str, str]) -> None:
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(rar['pwd-protected'])
    assert excinfo.value.args == ('Rar requires a password',)
