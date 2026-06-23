"""media_assets.py —— 项目媒体资源读取工具。

提供统一的图片目录扫描函数，避免各页面和报告模块重复实现。
所有路径使用 pathlib，不硬编码绝对路径。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def collect_images_from_dir(relative_dir: str) -> list[Path]:
    """从项目相对路径目录读取所有图片，返回排序后的 Path 列表。

    目录不存在或为空时返回空列表，不抛异常。
    """
    target = PROJECT_ROOT / relative_dir
    if not target.exists() or not target.is_dir():
        return []
    images = sorted(
        [p for p in target.iterdir()
         if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES]
    )
    return images


def pretty_image_name(path: Path, max_length: int = 60) -> str:
    """将文件名美化为可读图名。

    去掉扩展名，下划线替换为空格。如果美化后过短或过长，
    返回原始 stem 或截断版本。
    """
    stem = path.stem.strip()
    if not stem:
        return f"图片（{path.name}）"
    # 下划线/连字符 → 空格
    name = stem.replace("_", " ").replace("-", " ")
    # 去除多余空格
    name = " ".join(name.split())
    if not name:
        return f"图片（{path.name}）"
    if len(name) > max_length:
        name = name[:max_length].rstrip() + "…"
    return name


def render_image_grid(
    images: Iterable[Path],
    *,
    columns: int = 2,
    caption_fn=None,
) -> str | None:
    """返回一段简短摘要文本，供报告预览引用——不实际渲染 Streamlit 组件。
    如需在页面中渲染图片，请在页面文件中使用 st.image / st.columns。
    """
    img_list = list(images)
    if not img_list:
        return None
    if caption_fn is None:
        caption_fn = pretty_image_name
    lines = []
    for idx, img in enumerate(img_list, 1):
        lines.append(f"{idx}. {caption_fn(img)}（`{img.name}`）")
    return "\n".join(lines)
