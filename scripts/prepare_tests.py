"""Download files to be used in tests."""

from __future__ import annotations

import argparse
import os
import subprocess
import warnings
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests

TESTS = Path(__file__).parent.parent / 'tests'
TESTS_DATA_DIR = TESTS / 'data'


def download_mkv(mkv_dir_path: str | os.PathLike[str]) -> dict[str, str]:
    """Download mkv files to be used in tests."""
    # data_path = TESTS / 'data' / 'mkv'
    mkv_dir_path = Path(mkv_dir_path)
    mkv_dir_path.mkdir(parents=True, exist_ok=True)

    wanted_files = [f'test{i}.mkv' for i in range(1, 9)]

    # check for missing files
    missing_files = [f for f in wanted_files if not (mkv_dir_path / f).is_file()]
    if missing_files:
        # download matroska test suite
        r = requests.get(
            'https://downloads.sourceforge.net/project/matroska/test_files/matroska_test_w1_1.zip',
            timeout=20,
        )
        with ZipFile(BytesIO(r.content), 'r') as f:
            for missing_file in missing_files:
                f.extract(missing_file, mkv_dir_path)

    # populate a dict with mkv files
    files = {}
    for path in os.listdir(mkv_dir_path):
        if path not in wanted_files:
            continue
        name, _ = os.path.splitext(path)
        files[name] = os.fspath(mkv_dir_path / path)

    return files


def download_rar(rar_dir_path: str | os.PathLike[str]) -> dict[str, str]:
    """Download rar files to be used in tests."""
    # data_path = TESTS / 'data' / 'rar'
    rar_dir_path = Path(rar_dir_path)
    rar_dir_path.mkdir(parents=True, exist_ok=True)

    downloaded_files = {
        'pwd-protected': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-psw.rar?raw=true',
        'simple': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-quick-open.rar?raw=true',
    }

    files = {}
    # Add downloaded files
    for name, download_url in downloaded_files.items():
        filename = rar_dir_path / (name + '.rar')
        if not filename.is_file():
            r = requests.get(download_url, timeout=20)
            with filename.open('wb') as f:
                f.write(r.content)
        files[name] = os.fspath(filename)

    return files


def compress_to_rar(rar_dir_path: str | os.PathLike[str], mkv: dict[str, str]) -> dict[str, str]:
    """Compress mkv files to rar files to be used in tests."""
    # data_path = TESTS / 'data' / 'rar'
    rar_dir_path = Path(rar_dir_path)
    rar_dir_path.mkdir(parents=True, exist_ok=True)

    generated_files = {
        'video': [mkv.get('test1')],
        'videos': [mkv.get('test3'), mkv.get('test4'), mkv.get('test5')],
    }

    files = {}
    # Add generated files
    for name, videos in generated_files.items():
        existing_videos = [v for v in videos if v and os.path.isfile(v)]
        filename = os.fspath(rar_dir_path / (name + '.rar'))
        if not os.path.exists(filename):
            try:
                subprocess.run(  # noqa: S603
                    ['rar', 'a', '-ep', filename, *existing_videos],  # noqa: S607
                    check=True,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                warnings.warn('`rar` command took too long', UserWarning, stacklevel=2)
            except FileNotFoundError:
                # rar command line is not installed
                warnings.warn('rar is not installed', UserWarning, stacklevel=2)
        if os.path.exists(filename):
            files[name] = filename

    return files


def prepare_files(data_path: str | os.PathLike[str]) -> dict[str, dict[str, str]]:
    """Download and prepare files for tests."""
    data_path = Path(data_path)
    if not data_path.is_dir():
        data_path.mkdir(parents=True)

    # Download mkv files
    mkv = download_mkv(data_path / 'mkv')

    # Download rar files
    rar = download_rar(data_path / 'rar')

    # Compress mkv to rar
    rar.update(compress_to_rar(data_path / 'rar', mkv))

    return {'mkv': mkv, 'rar': rar}


def main() -> None:
    """Main script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default=TESTS_DATA_DIR)

    args = parser.parse_args()

    prepare_files(args.dir)


if __name__ == '__main__':
    main()
