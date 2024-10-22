"""Specialized :class:`~babelfiss.LanguageReverseConverter` converters to match the languages of the providers."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Tuple of language (alpha3, country, script), with country and script optional
    LanguageTuple = tuple[str, str | None, str | None]
