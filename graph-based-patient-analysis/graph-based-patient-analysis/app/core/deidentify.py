"""Minimal de-identification helpers.

This is a starting point loosely inspired by HIPAA Safe Harbor identifier
categories — it is NOT a certified or complete de-identification pipeline.
A real deployment needs a formal expert determination or full Safe Harbor
review, plus access controls and audit logging around any re-identification
key.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import date, timedelta

_DEFAULT_SALT = b"graph-based-patient-analysis-demo-salt"


def hash_identifier(raw_id: str, salt: bytes = _DEFAULT_SALT) -> str:
    """Deterministically pseudonymize an identifier (e.g. MRN, name) so the
    same source identifier always maps to the same pseudonym, without
    storing the original value.
    """
    return hmac.new(salt, raw_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def cap_age(age: int, cap: int = 90) -> int:
    """HIPAA Safe Harbor requires ages 90+ to be aggregated into a single
    '90+' bucket. We represent that as a capped integer here.
    """
    return min(age, cap)


def shift_date(original: date, offset_days: int) -> date:
    """Shift a date by a per-patient-consistent random offset, to preserve
    relative timing (e.g. days between encounters) while obscuring the
    real calendar dates.
    """
    return original + timedelta(days=offset_days)


def deterministic_offset(patient_raw_id: str, max_days: int = 365) -> int:
    """Derives a stable per-patient date-shift offset from their raw ID,
    so all of a patient's dates shift by the same amount (preserving
    intervals) without needing to store the offset separately.
    """
    digest = hashlib.sha256(patient_raw_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max_days
