"""Browser fullscreen helpers for the ARC two-dimensional workbench."""

from __future__ import annotations

import streamlit.components.v1 as components


def render_fullscreen_bridge(target_selector: str = ".arc-workbench-root") -> None:
    """Render a small bridge that enables browser fullscreen and ESC exit."""

    components.html(
        f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
html, body {{
  margin: 0;
  padding: 0;
  background: transparent;
  font-family: "Microsoft YaHei", Arial, sans-serif;
}}
.fullscreen-bridge {{
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}}
.fullscreen-bridge button {{
  min-height: 34px;
  border-radius: 9px;
  border: 1px solid #1565c0;
  background: #ffffff;
  color: #0b3a63;
  font-weight: 700;
  cursor: pointer;
  padding: 0 12px;
}}
.fullscreen-bridge .hint {{
  align-self: center;
  color: #607485;
  font-size: 12px;
}}
</style>
</head>
<body>
<div class="fullscreen-bridge">
  <span class="hint">ESC 可退出浏览器全屏</span>
  <button id="enter-fullscreen" type="button">进入浏览器全屏</button>
  <button id="exit-fullscreen" type="button">退出全屏</button>
</div>
<script>
const targetSelector = {target_selector!r};
function findTarget() {{
  const doc = window.parent.document;
  return doc.querySelector(targetSelector) || doc.documentElement;
}}
async function enterFullscreen() {{
  const target = findTarget();
  if (target.requestFullscreen) {{
    await target.requestFullscreen();
  }}
}}
async function exitFullscreen() {{
  if (window.parent.document.fullscreenElement && window.parent.document.exitFullscreen) {{
    await window.parent.document.exitFullscreen();
  }}
}}
window.parent.document.addEventListener("fullscreenchange", () => {{
  const active = !!window.parent.document.fullscreenElement;
  window.parent.document.documentElement.classList.toggle("arc-browser-fullscreen", active);
}});
window.parent.document.addEventListener("keydown", (event) => {{
  if (event.key === "Escape" && window.parent.document.fullscreenElement) {{
    exitFullscreen();
  }}
}}, true);
document.getElementById("enter-fullscreen").addEventListener("click", enterFullscreen);
document.getElementById("exit-fullscreen").addEventListener("click", exitFullscreen);
</script>
</body>
</html>
""",
        height=42,
        scrolling=False,
    )
