#!/usr/bin/env python3
"""
Scrape a Framer site and save fully-rendered HTML to a mirrored folder structure.
"""

import asyncio
import os
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://eager-room-678856.framer.app"
OUTPUT_DIR = Path.home() / "Downloads" / "my-site"
ZIP_PATH = Path.home() / "Downloads" / "my-site-final.zip"

PAGES = [
    ("/", "index.html"),
    ("/about", "about.html"),
    ("/work", "work.html"),
    ("/poppy", "poppy.html"),
    ("/trips", "trips.html"),
    ("/work/adtalem-global-education-inc", "work/adtalem-global-education-inc.html"),
    ("/work/progress-software-corporation", "work/progress-software-corporation.html"),
    ("/work/sandia-national-labs-datathon", "work/sandia-national-labs-datathon.html"),
    ("/work/goosehead-insurance", "work/goosehead-insurance.html"),
    ("/work/statistical-modeling-final-project", "work/statistical-modeling-final-project.html"),
    ("/trips/thailand", "trips/thailand.html"),
    ("/trips/taiwan", "trips/taiwan.html"),
    ("/trips/chengdu", "trips/chengdu.html"),
    ("/trips/macao", "trips/macao.html"),
    ("/trips/australia", "trips/australia.html"),
    ("/trips/new-zealand", "trips/new-zealand.html"),
    ("/trips/norway", "trips/norway.html"),
    ("/trips/banff", "trips/banff.html"),
    ("/trips/netherlands", "trips/netherlands.html"),
    ("/trips/uae", "trips/uae.html"),
    ("/trips/egypt", "trips/egypt.html"),
    ("/trips/peru", "trips/peru.html"),
    ("/trips/japan", "trips/japan.html"),
    ("/trips/london", "trips/london.html"),
    ("/trips/greece", "trips/greece.html"),
]


async def scrape_page(page, url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Scraping {url} -> {output_path.relative_to(OUTPUT_DIR.parent)}")
    await page.goto(url, wait_until="networkidle", timeout=60_000)
    # Extra wait to let lazy-loaded images / animations settle
    await page.wait_for_timeout(1500)
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    badge = soup.find("div", id="__framer-badge-container")
    if badge:
        badge.decompose()
        print("    Removed Framer badge")
    html = str(soup)
    output_path.write_text(html, encoding="utf-8")
    print(f"    Saved ({len(html):,} bytes)")


def zip_output() -> None:
    print(f"\nZipping {OUTPUT_DIR} -> {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in OUTPUT_DIR.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(OUTPUT_DIR.parent)
                zf.write(file, arcname)
    size_mb = ZIP_PATH.stat().st_size / 1_048_576
    print(f"Done! Archive size: {size_mb:.1f} MB -> {ZIP_PATH}")


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "work").mkdir(exist_ok=True)
    (OUTPUT_DIR / "trips").mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        print(f"Scraping {len(PAGES)} pages from {BASE_URL}\n")
        for path, filename in PAGES:
            url = BASE_URL + path
            output_path = OUTPUT_DIR / filename
            try:
                await scrape_page(page, url, output_path)
            except Exception as exc:
                print(f"    ERROR scraping {url}: {exc}")

        await browser.close()

    zip_output()


if __name__ == "__main__":
    asyncio.run(main())
