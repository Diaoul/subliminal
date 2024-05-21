"""Language converter for Shooter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter  # type: ignore[import-untyped]

from subliminal.exceptions import ConfigurationError

if TYPE_CHECKING:
    from . import LanguageTuple


class ShooterConverter(LanguageReverseConverter):
    """Language converter for Shooter."""

    def __init__(self) -> None:
        self.from_shooter: dict[str, LanguageTuple] = {'chn': ('zho',), 'eng': ('eng',)}
        self.to_shooter: dict[LanguageTuple, str] = {v: k for k, v in self.from_shooter.items()}
        self.codes = set(self.from_shooter.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3,) in self.to_shooter:
            return self.to_shooter[(alpha3,)]

        msg = f'Unsupported language code for shooter: {(alpha3, country, script)}'
        raise ConfigurationError(msg)

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_shooter:
            return self.from_shooter[code]

        msg = f'Unsupported language code for shooter: {code}'
        raise ConfigurationError(msg)
