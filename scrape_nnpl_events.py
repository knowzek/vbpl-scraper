# scrape_nnpl_events.py

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from bs4 import BeautifulSoup

BASE_CALENDAR = "https://public.tockify.com/feeds/nnlibrary/iframe/calendar"


def format_date_from_timestamp(ts):
    dt = datetime.fromtimestamp(int(ts) / 1000)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%b"), str(dt.day), str(dt.year)


async def scrape_nnpl_events(mode="all"):
    print("🧭 Launching Playwright for NNPL scrape...")
    events = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            extra_http_headers={
                "Referer": "https://library.nnva.gov/264/Events-Calendar",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        page = await context.new_page()
        await page.goto(BASE_CALENDAR, timeout=60000)

        try:
            await page.wait_for_selector("a.item", timeout=20000)
        except Exception as e:
            print("❌ Could not find event items — calendar may not be loaded properly.")
            content = await page.content()
            print("📄 Page content preview:\n", content[:1000])
            await browser.close()
            return []

        event_elements = await page.locator("a.item").all()
        print(f"🔗 Found {len(event_elements)} events on Tockify calendar")

        for el in event_elements:
            href = await el.get_attribute("href")
            if not href or not href.startswith("/nnlibrary/detail"):
                continue

            full_url = f"https://tockify.com{href}"
            print(f"📅 Visiting event: {full_url}")
            detail_page = await context.new_page()
            try:
                await detail_page.goto(full_url, timeout=20000)
                content = await detail_page.content()
                soup = BeautifulSoup(content, "html.parser")

                title = soup.select_one(".title-text")
                title = title.get_text(strip=True) if title else "Untitled Event"

                description = soup.select_one(".description")
                description = description.get_text("\n\n", strip=True) if description else ""

                time_tag = soup.select_one(".time")
                time_text = time_tag.get_text(strip=True) if time_tag else "All Day Event"

                location_tag = soup.select_one(".location")
                location = location_tag.get_text(strip=True) if location_tag else ""

                parts = href.strip("/").split("/")
                event_id = parts[-2]
                timestamp = parts[-1]
                event_date, month, day, year = format_date_from_timestamp(timestamp)

                events.append({
                    "Event Name": title,
                    "Event Link": full_url,
                    "Event Status": "Available",
                    "Time": time_text,
                    "Ages": "",
                    "Location": location,
                    "Month": month,
                    "Day": day,
                    "Year": year,
                    "Event Date": event_date,
                    "Event End Date": event_date,
                    "Event Description": description,
                    "Series": "",
                    "Program Type": ""
                })

            except Exception as e:
                print(f"⚠️ Failed to process event: {full_url} — {e}")
            finally:
                await detail_page.close()

        await browser.close()

    print(f"✅ Scraped {len(events)} NNPL events.")
    return events


if __name__ == "__main__":
    asyncio.run(scrape_nnpl_events())
