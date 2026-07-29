"""Unit tests for deterministic intent classification."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agents.intent import classify_intent
from app.models.schemas import Intent


def test_booking():
    assert classify_intent("Book a bus from Chennai to Madurai") == Intent.BOOKING
    assert classify_intent("search buses to coimbatore") == Intent.BOOKING


def test_policy():
    assert classify_intent("What is the cancellation policy?") == Intent.POLICY
    assert classify_intent("baggage allowance") == Intent.POLICY


def test_complaint():
    assert classify_intent("I want to complain about a delay") == Intent.COMPLAINT


def test_tracking():
    assert classify_intent("Where is my bus? track eta") == Intent.TRACKING


def test_greeting():
    assert classify_intent("Hello") == Intent.GREETING
    assert classify_intent("hi there") == Intent.GREETING


def test_out_of_scope():
    assert classify_intent("Tell me a joke") == Intent.OUT_OF_SCOPE
    assert classify_intent("What is the weather in Paris?") == Intent.OUT_OF_SCOPE
    assert classify_intent("Write python code") == Intent.OUT_OF_SCOPE


def test_ticket():
    assert classify_intent("Show my PNR and download PDF") == Intent.TICKET
