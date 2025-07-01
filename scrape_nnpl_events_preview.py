# scrape_nnpl_events_preview.py

import asyncio
from playwright.async_api import async_playwright

async def scrape_nnpl_preview():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("🌐 Navigating to NNPL calendar...")
        await page.goto("https://library.nnva.gov/264/Events-Calendar", timeout=60000)
        await page.wait_for_timeout(5000)  # Give extra time for the calendar to load

        # Try to grab the iframe if the calendar is embedded
        iframes = page.frames
        for frame in iframes:
            if "civic" in (frame.url or "").lower():
                print(f"🔍 Found calendar iframe: {frame.url}")
                calendar_frame = frame
                break
        else:
            calendar_frame = page.main_frame
            print("⚠️ No iframe found — scraping main frame instead.")

        # Dump all divs with class or id matching 'event', or list item containers
        event_selectors = [
            "[class*='event']",
            "[id*='event']",
            ".event-list-item",
            ".fc-event",  # common for fullcalendar.js
        ]

        found_any = False
        for selector in event_selectors:
            try:
                elements = await calendar_frame.query_selector_all(selector)
                if elements:
                    found_any = True
                    print(f"\n🧩 Found {len(elements)} elements with selector '{selector}' — showing first 3:\n")
                    for i, el in enumerate(elements[:3]):
                        html = await el.inner_html()
                        print(f"--- Event {i+1} ---\n{html}\n")
                    break
            except Exception as e:
                continue

        if not found_any:
            print("❌ No event containers found. The site may rely heavily on JS-based modals or AJAX.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_nnpl_preview())
