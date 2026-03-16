"""Centralized CIK normalization — single source of truth.

Previously duplicated in:
- search_edgar.py
- extract_catalysts.py
- fetch_financials.py
"""

from __future__ import annotations


def normalize_cik(cik: str) -> tuple[str, str]:
    """Return (unpadded, padded) CIK representations.

    SEC submissions use a zero-padded CIK (10 digits), while archive
    document URLs use the unpadded value.

    Args:
        cik: Raw CIK string (may contain leading zeros or non-digit chars).

    Returns:
        Tuple of (cik_unpadded, cik_padded).

    Raises:
        ValueError: If the input contains no digits.
    """
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError(f"CIK must contain at least one digit, got: {cik!r}")

    cik_unpadded = digits.lstrip("0") or "0"
    cik_padded = cik_unpadded.zfill(10)
    return cik_unpadded, cik_padded
