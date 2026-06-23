"""Safe rendering helpers for project visual assets."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_asset_path(relative_path: str) -> Path:
    """Return an asset path under the project root."""
    clean_path = relative_path.replace("\\", "/").lstrip("/")
    return PROJECT_ROOT / clean_path


def asset_exists(relative_path: str) -> bool:
    """Return whether an asset exists under the project root."""
    return resolve_asset_path(relative_path).exists()


def render_asset_image(
    relative_path: str,
    caption: str,
    title: str | None = None,
) -> bool:
    """Render an image if present and show a friendly message if missing."""
    path = resolve_asset_path(relative_path)
    if title:
        st.markdown(f"**{title}**")
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
        return True
    st.info(f"图片资源未找到：{relative_path}")
    return False
