# mypy: disallow-untyped-defs
# ruff: noqa: S603, S607
"""Invoke development tasks."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from subprocess import check_call, check_output

from colorama import Fore, init

VERSION_REGEX = r'(__version__(?:\s*\:\s*str)?\s*=\s*(?P<quote>[\'"]))(?P<version>\d+\.\d+\.\d+.*)((?P=quote))'
VERSION_FILE = 'subliminal/__init__.py'


def announce(version: str, template_name: str, doc_version: str) -> None:
    """Generates a new release announcement entry in the docs."""
    # Get our list of authors
    stdout = check_output(['git', 'describe', '--abbrev=0', '--tags'], encoding='UTF-8')
    last_version = stdout.strip()

    stdout = check_output(['git', 'log', f'{last_version}..HEAD', '--format=%aN'], encoding='UTF-8')

    contributors = {name for name in stdout.splitlines() if not name.endswith('[bot]') and name != 'pytest bot'}

    template_text = Path(__file__).parent.joinpath(template_name).read_text(encoding='UTF-8')

    contributors_text = '\n'.join(f'* {name}' for name in sorted(contributors)) + '\n'
    text = template_text.format(version=version, contributors=contributors_text, doc_version=doc_version)

    target = Path(__file__).parent.joinpath(f'../doc/en/announce/release-{version}.rst')
    target.write_text(text, encoding='UTF-8')
    print(f'{Fore.CYAN}[generate.announce] {Fore.RESET}Generated {target.name}')

    # Update index with the new release entry
    index_path = Path(__file__).parent.joinpath('../doc/en/announce/index.rst')
    lines = index_path.read_text(encoding='UTF-8').splitlines()
    indent = '   '
    for index, line in enumerate(lines):
        if line.startswith(f'{indent}release-'):
            new_line = indent + target.stem
            if line != new_line:
                lines.insert(index, new_line)
                index_path.write_text('\n'.join(lines) + '\n', encoding='UTF-8')
                print(f'{Fore.CYAN}[generate.announce] {Fore.RESET}Updated {index_path.name}')
            else:
                print(f'{Fore.CYAN}[generate.announce] {Fore.RESET}Skip {index_path.name} (already contains release)')
            break

    check_call(['git', 'add', str(target)])


def regen(version: str) -> None:
    """Call regendoc tool to update examples and pytest output in the docs."""
    print(f'{Fore.CYAN}[generate.regen] {Fore.RESET}Updating docs')
    check_call(
        ['tox', '-e', 'regen'],
        env={**os.environ, 'SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYTEST': version},
    )


def fix_formatting() -> None:
    """Runs pre-commit in all files to ensure they are formatted correctly."""
    print(f'{Fore.CYAN}[generate.fix_formatting] {Fore.RESET}Fixing formatting using pre-commit')
    check_call(['tox', '-e', 'pre-commit'])


def check_docs() -> None:
    """Runs sphinx-build to check docs."""
    print(f'{Fore.CYAN}[generate.check_docs] {Fore.RESET}Checking docs')
    check_call(['tox', '-e', 'docs'])


def changelog(version: str, *, write_out: bool = False) -> None:
    """Call towncrier to generate the changelog."""
    addopts = [] if write_out else ['--draft']
    check_call(['towncrier', 'build', '--yes', '--version', version, *addopts])


def bump_version(version: str) -> None:
    """Bump the version in the file."""
    print(f'{Fore.CYAN}[generate.bump_version] {Fore.RESET}Bump version to {version} in {VERSION_FILE}')
    pattern = re.compile(VERSION_REGEX)
    file = Path(__file__).parent / '..' / VERSION_FILE

    content = file.open().read()
    repl = r'\g<1>' + version + r'\g<2>'
    new_content, n_matches = re.subn(pattern, repl, content)
    if n_matches == 0:
        print()
        print(f'No `__version__` definition was found in file {VERSION_FILE}')
        print()
        return

    # Update file content
    file.open('w').write(new_content)


def pre_release(version: str, template_name: str, doc_version: str, *, skip_check_docs: bool) -> None:
    """Generates new docs and update the version."""
    # announce(version, template_name, doc_version)
    # regen(version)
    changelog(version, write_out=True)
    fix_formatting()
    if not skip_check_docs:
        check_docs()
    # bump_version(version)

    msg = f'Prepare release version {version}'
    check_call(['git', 'commit', '-a', '-m', msg])

    print()
    print(f'{Fore.CYAN}[generate.pre_release] {Fore.GREEN}All done!')
    print()
    print('Please push your branch and open a PR.')


def main() -> None:  # noqa: D103
    init(autoreset=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('version', help='Release version')
    parser.add_argument(
        'template_name',
        nargs='?',
        help='Name of template file to use for release announcement',
        default='',
    )
    parser.add_argument(
        'doc_version',
        nargs='?',
        help='For prereleases, the version to link to in the docs',
        default='',
    )
    parser.add_argument('--skip-check-docs', help='Skip doc tests', action='store_false', default=True)
    options = parser.parse_args()
    pre_release(
        options.version,
        options.template_name,
        options.doc_version,
        skip_check_docs=options.skip_check_docs,
    )


if __name__ == '__main__':
    main()
