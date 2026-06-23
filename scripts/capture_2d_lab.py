"""Capture verified screenshots for the two-dimensional lab page.

The script uses the Playwright Node package through npx so it can work even
when Python Playwright is not installed. It refuses to save screenshots when
the browser is on the wrong page, an unrelated application, or a mostly blank
page.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "playwright"
DEFAULT_URL = "http://localhost:8501"
PAGE_SLUG = "二维交互实验台"
FORBIDDEN_TEXT = (
    "Projects",
    "Page not found",
)


def _wait_for_streamlit(url: str, timeout_s: int = 45) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def _start_streamlit(url: str) -> subprocess.Popen[str] | None:
    if _wait_for_streamlit(url, timeout_s=3):
        return None
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    log_path = OUTPUT_DIR / "streamlit-capture.log"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/main.py", "--server.headless=true"],
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    if not _wait_for_streamlit(url, timeout_s=60):
        process.terminate()
        raise RuntimeError(f"Streamlit did not become ready at {url}. See {log_path}")
    return process


def capture(url: str) -> None:
    """Run the browser capture workflow with strict page assertions."""

    process = _start_streamlit(url)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        local_playwright = shutil.which("playwright.exe") or shutil.which("playwright")
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if not local_playwright and not npx:
            raise RuntimeError("Neither playwright nor npx was found on PATH")
        page_url = f"{url.rstrip('/')}/{quote(PAGE_SLUG)}"
        captures = [
            ("standard", f"{page_url}?capture=standard", OUTPUT_DIR / "verified-2d-lab-standard.png"),
            ("large-canvas", f"{page_url}?capture=large", OUTPUT_DIR / "verified-2d-lab-large-canvas.png"),
            ("hotspots", f"{page_url}?capture=hotspots", OUTPUT_DIR / "verified-2d-lab-hotspots.png"),
            ("safety-alert", f"{page_url}?capture=alert", OUTPUT_DIR / "verified-2d-lab-safety-alert.png"),
            ("legend", f"{page_url}?capture=legend", OUTPUT_DIR / "verified-2d-lab-legend.png"),
        ]
        for label, target_url, output in captures:
            temp_output = output.with_suffix(".tmp.png")
            if temp_output.exists():
                temp_output.unlink()
            if local_playwright:
                command = [
                    local_playwright,
                    "screenshot",
                    "--viewport-size=1440,980",
                    "--wait-for-timeout=7000",
                    target_url,
                    str(temp_output),
                ]
            else:
                command = [
                    npx,
                    "--yes",
                    "playwright",
                    "screenshot",
                    "--viewport-size=1440,980",
                    "--wait-for-timeout=7000",
                    target_url,
                    str(temp_output),
                ]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout)
            _assert_screenshot_file(temp_output, label)
            temp_output.replace(output)
            print(f"{label}: {output}")
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def _assert_screenshot_file(path: Path, label: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{label}: screenshot was not created")
    data = path.read_bytes()
    if len(data) < 80_000:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"{label}: screenshot is too small, likely blank or wrong page")
    forbidden_bytes = [text.encode("utf-8", errors="ignore") for text in FORBIDDEN_TEXT]
    if any(item and item in data for item in forbidden_bytes):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"{label}: forbidden text marker found in screenshot bytes")
    with Image.open(path) as image:
        crop = image.crop((300, 260, min(image.width, 1360), min(image.height, 960))).convert("RGB")
        stat = ImageStat.Stat(crop)
        if max(stat.stddev) < 8:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"{label}: screenshot content area is visually too uniform")


def main() -> int:
    try:
        capture(DEFAULT_URL)
    except Exception as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
