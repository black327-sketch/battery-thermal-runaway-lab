"""Compatibility wrapper for the floating AI companion.

The previous page-embedded assistant UI has been removed. Existing pages may
still import ``render_teaching_ai_widget``; this wrapper renders only the
draggable floating companion.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.components.floating_ai_companion import render_floating_ai_companion


def render_teaching_ai_widget(
    *,
    page_name: str,
    experiment_state: Mapping[str, Any] | None = None,
    assessment: Mapping[str, Any] | None = None,
    key_prefix: str = "global",
) -> None:
    render_floating_ai_companion(
        page_name=page_name,
        experiment_context=experiment_state,
        assessment=assessment,
        key_prefix=key_prefix,
    )
