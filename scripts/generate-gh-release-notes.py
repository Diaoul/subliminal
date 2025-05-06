# mypy: disallow-untyped-defs
"""Generate a Markdown file containing only the changelog entries of a specific release.

The markdown file is used as body for the GitHub Release during deploy (see workflows/publish.yml).

The script requires ``pandoc`` to be previously installed in the system -- we need to convert from RST (the format of
our HISTORY) into Markdown (which is required by GitHub Releases).

Requires Python3.6+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pypandoc

HISTORY_FILE = 'HISTORY.rst'


def extract_changelog_entries_for(history_file: str, version: str) -> str:
    """Extract the changelog for the specified version."""
    p = Path(__file__).parent.parent / history_file
    changelog_lines = p.read_text(encoding='UTF-8').splitlines()

    title_regex = re.compile(r'^(\d+\.\d+\.\d+\w*)( \(\d{4}-\d{2}-\d{2}\))?$')
    consuming_version = False
    version_lines = []
    for line in changelog_lines:
        # Make sure backticks are doubled
        # line = re.sub('([^`])`([^`#])', r'\g<1>``\g<2>', line)
        m = title_regex.match(line)
        if m:
            # Found the version we want: start to consume lines until we find the next version title.
            if m.group(1) == version:
                consuming_version = True
            # Found a new version title while parsing the version we want: break out.
            elif consuming_version:
                break
        if consuming_version:
            version_lines.append(line)

    return '\n'.join(version_lines)


def convert_rst_to_md(text: str) -> str:
    """Convert the text from rst to md."""
    result = pypandoc.convert_text(
        text,
        'md',
        format='rst',
        extra_args=['--wrap=preserve'],
    )
    if not isinstance(result, str):
        msg = f'Could not convert text:\n{text}'
        raise TypeError(msg)
    return result


def main() -> int:
    """Generate release notes."""
    parser = argparse.ArgumentParser()
    parser.add_argument('version')
    parser.add_argument('output', default='scripts/release-notes.md')

    args = parser.parse_args()

    print(f'Generating GitHub release notes for version {args.version}')
    rst_body = extract_changelog_entries_for(HISTORY_FILE, args.version)
    if not rst_body:
        print(f'Cannot extract notes about version {args.version} from {HISTORY_FILE}')
        return 1

    md_body = convert_rst_to_md(rst_body)
    Path(args.output).write_text(md_body, encoding='UTF-8')
    print()
    print(f'Done: {args.output}')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
