"""Deterministic intent classification BEFORE any LLM / agent / RAG call."""

import re
from typing import Tuple

from app.models.schemas import Intent

# Keyword patterns – order matters for priority
INTENT_PATTERNS: list[Tuple[Intent, list[str]]] = [
    (
        Intent.BOOKING,
        [
            r"\bbook\b",
            r"\bsearch\b",
            r"\bbus(es)?\b",
            r"\bticket(s)?\s*(for|to|from)?\b",
            r"\bseat(s)?\b",
            r"\bfare\b",
            r"\breserv",
            r"\bavailability\b",
            r"from\s+\w+\s+to\s+\w+",
            r"chennai|madurai|coimbatore|trichy",
        ],
    ),
    (
        Intent.TICKET,
        [
            r"\bpnr\b",
            r"\bmy\s+ticket",
            r"\bdownload\s+ticket",
            r"\bpdf\b",
            r"\bqr\b",
            r"\botp\b",
            r"\bverify\b",
        ],
    ),
    (
        Intent.TRACKING,
        [
            r"\btrack\b",
            r"\blive\s+location",
            r"\bwhere\s+is\s+(my\s+)?bus",
            r"\beta\b",
            r"\barrival\b",
            r"\bprogress\b",
        ],
    ),
    (
        Intent.JOURNEY,
        [
            r"\bjourney\b",
            r"\btimeline\b",
            r"\balert\b",
            r"\bdestination\b",
            r"\bstops?\b",
        ],
    ),
    (
        Intent.COMPLAINT,
        [
            r"\bcomplain",
            r"\bissue\b",
            r"\bproblem\b",
            r"\brefund\b",
            r"\bcancel",
            r"\bdelay\b",
            r"\brude\b",
            r"\bdirty\b",
        ],
    ),
    (
        Intent.FEEDBACK,
        [
            r"\bfeedback\b",
            r"\brating\b",
            r"\breview\b",
            r"\bsuggest",
            r"\bthank",
        ],
    ),
    (
        Intent.POLICY,
        [
            r"\bpolicy\b",
            r"\bcancellation\s+policy",
            r"\bbaggage\b",
            r"\bluggage\b",
            r"\brules?\b",
            r"\bterms\b",
            r"\brefund\s+policy",
            r"\bchild\s+fare",
        ],
    ),
    (
        Intent.GREETING,
        [
            r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|namaste)\b",
            r"\bhow\s+are\s+you\b",
        ],
    ),
]


OUT_OF_SCOPE_HINTS = [
    r"\bweather\b",
    r"\bnews\b",
    r"\bstock\b",
    r"\bcook\b",
    r"\brecipe\b",
    r"\bcode\b",
    r"\bprogram\b",
    r"\bjoke\b",
    r"\bstory\b",
    r"\bpoem\b",
    r"\bmath\b",
    r"\btranslate\b",
]


def classify_intent(message: str) -> Intent:
    """Rule-based classifier – no LLM. Returns Out-of-Scope when unclear."""
    text = message.strip().lower()
    if not text:
        return Intent.GREETING

    for pattern in OUT_OF_SCOPE_HINTS:
        if re.search(pattern, text, re.I):
            return Intent.OUT_OF_SCOPE

    scores: dict[Intent, int] = {}
    for intent, patterns in INTENT_PATTERNS:
        score = 0
        for p in patterns:
            if re.search(p, text, re.I):
                score += 1
        if score:
            scores[intent] = score

    if not scores:
        return Intent.OUT_OF_SCOPE

    return max(scores, key=scores.get)  # type: ignore[arg-type]


def is_in_scope(intent: Intent) -> bool:
    return intent != Intent.OUT_OF_SCOPE
