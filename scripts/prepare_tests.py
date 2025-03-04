"""Download files to be used in tests."""

from __future__ import annotations

import os
import subprocess
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests

TESTS = Path(__file__).parent / 'tests'


def download_mkvs(data_path: str | os.PathLike[str]) -> dict[str, str]:
    """Download mkv files to be used in tests."""
    # data_path = TESTS / 'data' / 'mkv'
    data_path = Path(data_path)
    if not data_path.is_dir():
        os.makedirs(data_path)

    wanted_files = [f'test{i}.mkv' for i in range(1, 9)]

    # check for missing files
    missing_files = [f for f in wanted_files if not (data_path / f).is_file()]
    if missing_files:
        # download matroska test suite
        r = requests.get(
            'https://downloads.sourceforge.net/project/matroska/test_files/matroska_test_w1_1.zip',
            timeout=20,
        )
        with ZipFile(BytesIO(r.content), 'r') as f:
            for missing_file in missing_files:
                f.extract(missing_file, data_path)

    # populate a dict with mkv files
    files = {}
    for path in os.listdir(data_path):
        if path not in wanted_files:
            continue
        name, _ = os.path.splitext(path)
        files[name] = os.fspath(data_path / path)

    return files


def download_rars(data_path: str | os.PathLike[str]) -> dict[str, str]:
    """Download rar files to be used in tests."""
    # data_path = TESTS / 'data' / 'rar'
    data_path = Path(data_path)
    if not data_path.is_dir():
        os.makedirs(data_path)

    downloaded_files = {
        'pwd-protected': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-psw.rar?raw=true',
        'simple': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-quick-open.rar?raw=true',
    }

    files = {}
    # Add downloaded files
    for name, download_url in downloaded_files.items():
        filename = data_path / (name + '.rar')
        if not filename.is_file():
            r = requests.get(download_url, timeout=20)
            with filename.open('wb') as f:
                f.write(r.content)
        files[name] = os.fspath(filename)

    return files


def compress_to_rar(data_path: str | os.PathLike[str], mkv: dict[str, str]) -> dict[str, str]:
    """Compress mkv files to rar files to be used in tests."""
    data_path = TESTS / 'data' / 'rar'
    if not data_path.is_dir():
        os.makedirs(data_path)

    downloaded_files = {
        'pwd-protected': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-psw.rar?raw=true',
        'simple': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-quick-open.rar?raw=true',
    }

    generated_files = {
        'video': [mkv.get('test1')],
        'videos': [mkv.get('test3'), mkv.get('test4'), mkv.get('test5')],
    }

    files = {}
    # Add downloaded files
    for name, download_url in downloaded_files.items():
        filename = os.path.join(data_path, name + '.rar')
        if not os.path.exists(filename):
            r = requests.get(download_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
        files[name] = filename

    # Add generated files
    for name, videos in generated_files.items():
        existing_videos = [v for v in videos if v and os.path.isfile(v)]
        filename = os.path.join(data_path, name + '.rar')
        if not os.path.exists(filename):
            try:
                subprocess.run(['rar', 'a', '-ep', filename, *existing_videos], check=True)  # noqa: S603, S607
            except FileNotFoundError:
                # rar command line is not installed
                print('rar is not installed')
        if os.path.exists(filename):
            files[name] = filename

    return files
