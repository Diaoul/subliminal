from __future__ import annotations

from difflib import SequenceMatcher

import pytest

from subliminal.cli import generate_default_config

# Core test
pytestmark = [
    pytest.mark.core,
]


def test_generated_config() -> None:
    doc = generate_default_config(commented=False)
    doc_commented = generate_default_config(commented=True)

    doc_force_commented = ''.join(
        [
            f'# {line}' if line and not line.startswith(('[', '#', '\n')) else line
            for line in doc.splitlines(keepends=True)
        ]
    )

    x = SequenceMatcher(None, doc_commented, doc_force_commented)
    blocks = x.get_matching_blocks()

    assert len(blocks) == 2

    length = len(doc_commented)
    for match in blocks:
        assert match.size == 0 or match.size == length
