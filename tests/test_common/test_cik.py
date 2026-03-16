"""Tests for the centralized CIK normalization utility."""

import pytest
from super_agents.common.cik import normalize_cik


def test_normalize_cik_standard():
    unpadded, padded = normalize_cik("0000744218")
    assert unpadded == "744218"
    assert padded == "0000744218"


def test_normalize_cik_unpadded_input():
    unpadded, padded = normalize_cik("744218")
    assert unpadded == "744218"
    assert padded == "0000744218"


def test_normalize_cik_short():
    unpadded, padded = normalize_cik("42")
    assert unpadded == "42"
    assert padded == "0000000042"


def test_normalize_cik_zero():
    unpadded, padded = normalize_cik("0000000000")
    assert unpadded == "0"
    assert padded == "0000000000"


def test_normalize_cik_with_prefix():
    unpadded, padded = normalize_cik("CIK0000744218")
    assert unpadded == "744218"
    assert padded == "0000744218"


def test_normalize_cik_no_digits_raises():
    with pytest.raises(ValueError, match="must contain at least one digit"):
        normalize_cik("abc")


def test_normalize_cik_empty_raises():
    with pytest.raises(ValueError, match="must contain at least one digit"):
        normalize_cik("")
