"""Generate banner PNGs from banner.html using Playwright."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HTML = HERE / "banner.html"
OUT_DIR = HERE

SIZES = {
    "lorekeeper-banner-1200x630.png": (1200, 630),
    "lorekeeper-banner-square.png": (1080, 1080),
    "lorekeeper-banner-thumb.png": (600, 400),
}


def generate():
    html = HTML.read_text()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html, wait_until="networkidle")

        for name, (w, h) in SIZES.items():
            path = OUT_DIR / name
            if (w, h) != (1200, 630):
                page.set_viewport_size({"width": w, "height": h})
            page.screenshot(path=str(path), full_page=True)
            print(f"  ✓ {name}  ({w}×{h})")

        browser.close()


if __name__ == "__main__":
    generate()