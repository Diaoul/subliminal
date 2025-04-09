# mypy: disallow-untyped-defs
# ruff: noqa: S603, S607
"""Prepare release pull-request.

This script is part of the pytest release process which is triggered manually in the Actions
tab of the repository.

The user will need to enter the base branch to start the release from (for example
``6.1.x`` or ``main``) and if it should be a major release.

The appropriate version will be obtained based on the given branch automatically.

After that, it will create a release using the `release` tox environment, and push a new PR.

Note: the script uses the `gh` command-line tool, so `GH_TOKEN` must be set in the environment.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from subprocess import check_call, check_output, run

from colorama import Fore, init


class InvalidFeatureRelease(Exception):  # noqa: D101
    pass


SLUG = 'getzze/subliminal'

PR_BODY = """\
Created by the [prepare release pr]\
(https://github.com/Diaoul/subliminal/actions/workflows/prepare-release-pr.yaml) workflow.

Once all builds pass and it has been **approved** by one or more maintainers and **merged**,
it will trigger the [publish]\
(https://github.com/Diaoul/subliminat/actions/workflows/publish.yaml) workflow that will:

* Tag the commit with version `{version}`.
* Create a Github release for version `{version}`.
* Upload version `{version}` to Pypi.

This is all done automatically when this PR is merged.
"""


def find_next_version(base_branch: str, *, is_major: bool, is_minor: bool, prerelease: str) -> str:
    """Find the next version, being a major, minor or patch bump."""
    output = check_output(['git', 'tag'], encoding='UTF-8')
    valid_versions: list[tuple[int, ...]] = []
    for v in output.splitlines():
        # Match 'major.minor.patch', do not match tags of pre-release versions
        m = re.match(r'v?(\d+)\.(\d+)\.(\d+)$', v.strip())
        if m:
            valid_versions.append(tuple(int(x) for x in m.groups()))

    valid_versions.sort()
    last_version = valid_versions[-1]

    print(f'Current version from git tag: {Fore.CYAN}{last_version}')
    bump_str = 'major' if is_major else 'minor' if is_minor else 'patch'
    print(f'Bump {bump_str} version')

    if is_major:
        return f'{last_version[0] + 1}.0.0{prerelease}'
    if is_minor:
        return f'{last_version[0]}.{last_version[1] + 1}.0{prerelease}'
    return f'{last_version[0]}.{last_version[1]}.{last_version[2] + 1}{prerelease}'


def prepare_release_pr(base_branch: str, bump: str, prerelease: str) -> None:
    """Find the bumped version and make a release PR."""
    print()
    print(f'Processing release for branch {Fore.CYAN}{base_branch}')

    check_call(['git', 'checkout', f'origin/{base_branch}'])

    changelog = Path('changelog.d')

    breaking = list(changelog.glob('*.breaking.rst'))
    is_major = bool(breaking) or bool(bump == 'major')
    features = list(changelog.glob('*.change.rst'))
    is_minor = not is_major and (bool(features) or bool(bump == 'minor'))

    try:
        version = find_next_version(
            base_branch,
            is_major=is_major,
            is_minor=is_minor,
            prerelease=prerelease,
        )
    except InvalidFeatureRelease as e:
        print(f'{Fore.RED}{e}')
        raise SystemExit(1) from None

    print(f'Version: {Fore.CYAN}{version}')

    # for security, the PR must be from a 'releases/*' branch AND have the 'release' label
    release_branch = f'releases/{version}'
    label = 'release'

    run(
        ['git', 'config', 'user.name', 'subliminal bot'],
        check=True,
    )
    run(
        ['git', 'config', 'user.email', 'diaoulael@gmail.com'],
        check=True,
    )

    run(
        ['git', 'checkout', '-b', release_branch, f'origin/{base_branch}'],
        check=True,
    )

    print(f'Branch {Fore.CYAN}{release_branch}{Fore.RESET} created.')

    if is_major:
        template_name = 'release.major.rst'
    elif prerelease:
        template_name = 'release.pre.rst'
    elif is_minor:
        template_name = 'release.minor.rst'
    else:
        template_name = 'release.patch.rst'

    # important to use tox here because we have changed branches, so dependencies
    # might have changed as well
    cmdline = [
        'tox',
        '-e',
        'release',
        '--',
        version,
        template_name,
        release_branch,  # doc_version
    ]
    print('Running', ' '.join(cmdline))
    run(
        cmdline,
        check=True,
    )

    run(
        ['git', 'push', 'origin', f'HEAD:{release_branch}', '--force'],
        check=True,
    )
    print(f'Branch {Fore.CYAN}{release_branch}{Fore.RESET} pushed.')

    body = PR_BODY.format(version=version)
    run(
        [
            'gh',
            'pr',
            'new',
            f'--base={base_branch}',
            f'--head={release_branch}',
            f'--title=Release {version}',
            f'--body={body}',
            f'--label={label}',
        ],
        check=True,
    )


def main() -> None:  # noqa: D103
    init(autoreset=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('base_branch')
    parser.add_argument('--bump', default='')
    parser.add_argument('--prerelease', default='')
    options = parser.parse_args()
    prepare_release_pr(
        base_branch=options.base_branch,
        bump=options.bump,
        prerelease=options.prerelease,
    )


if __name__ == '__main__':
    main()
