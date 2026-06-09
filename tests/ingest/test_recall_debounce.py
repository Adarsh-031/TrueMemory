"""Tests for the first-message recall debounce (issue #561).

SessionStart already searches TrueMemory and injects up to 25 memories. The
UserPromptSubmit hook's per-message auto-recall is therefore redundant on the
first prompt of a session. These tests cover the one-shot, time-windowed
debounce marker that lets UserPromptSubmit skip that redundant recall.

Covers:
  - mark_recall_injected / consume_recall_injected round-trip and semantics
  - _try_auto_recall short-circuits (no recall work) when the marker is fresh
"""
from __future__ import annotations

import time

import pytest

from truememory.ingest.hooks import _shared
from truememory.ingest.hooks import user_prompt_submit as ups


@pytest.fixture
def marker_dir(monkeypatch, tmp_path):
    """Point the recall-marker store at an isolated temp dir."""
    d = tmp_path / "recall_markers"
    monkeypatch.setattr(_shared, "RECALL_MARKER_DIR", d)
    return d


class TestRecallMarker:
    def test_mark_then_consume_is_true(self, marker_dir):
        _shared.mark_recall_injected("session-abc")
        assert _shared.consume_recall_injected("session-abc") is True

    def test_consume_is_one_shot(self, marker_dir):
        """Only the first prompt is debounced; the marker is consumed."""
        _shared.mark_recall_injected("session-abc")
        assert _shared.consume_recall_injected("session-abc") is True
        assert _shared.consume_recall_injected("session-abc") is False

    def test_consume_without_marker_is_false(self, marker_dir):
        assert _shared.consume_recall_injected("never-marked") is False

    def test_stale_marker_is_not_fresh_and_is_cleaned(self, marker_dir):
        _shared.mark_recall_injected("session-old")
        marker = marker_dir / "session-old"
        marker.write_text(str(time.time() - 10_000), encoding="utf-8")
        assert _shared.consume_recall_injected("session-old", within_seconds=60) is False
        # Stale markers are still removed so the dir self-cleans.
        assert not marker.exists()

    def test_within_seconds_zero_disables_debounce(self, marker_dir):
        _shared.mark_recall_injected("session-abc")
        assert _shared.consume_recall_injected("session-abc", within_seconds=0) is False

    def test_empty_session_id_is_safe(self, marker_dir):
        assert _shared.consume_recall_injected("") is False
        # Must not raise even when there is nothing to mark.
        _shared.mark_recall_injected("")

    def test_corrupt_marker_is_false(self, marker_dir):
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / "session-bad").write_text("not-a-timestamp", encoding="utf-8")
        assert _shared.consume_recall_injected("session-bad") is False


class TestAutoRecallGate:
    def test_fresh_marker_short_circuits_recall(self, marker_dir, monkeypatch):
        """A fresh marker makes _try_auto_recall return None before doing any
        recall work (no detection, no Memory load)."""
        def _boom(*_a, **_k):
            raise AssertionError("recall work must not run when marker is fresh")

        monkeypatch.setattr(ups, "_detect_recall", _boom)
        _shared.mark_recall_injected("session-first")

        result = ups._try_auto_recall(
            "what's my favorite editor", "", "", session_id="session-first"
        )
        assert result is None

    def test_no_marker_allows_recall_detection(self, marker_dir, monkeypatch):
        """Without a marker, the gate falls through to normal recall detection."""
        called = {}

        def _detect(prompt):
            called["prompt"] = prompt
            return False  # short-circuit before Memory load

        monkeypatch.setattr(ups, "_detect_recall", _detect)
        result = ups._try_auto_recall(
            "what's my favorite editor", "", "", session_id="session-fresh"
        )
        assert result is None
        assert called["prompt"] == "what's my favorite editor"
