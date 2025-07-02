# scrape_nnpl_events.py

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from bs4 import BeautifulSoup

BASE_CALENDAR = "https://library.nnva.gov/264/Events-Calendar"


def format_date_from_text(raw):
    try:
        dt = datetime.strptime(raw, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%b"), str(dt.day), str(dt.year)
    except:
        return "", "", "", ""


async def scrape_nnpl_events(mode="all"):
    print("🧭 Launching Playwright for NNPL scrape...")
    events = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
        page = await browser.new_page()
        await page.goto(BASE_CALENDAR, timeout=60000)
        await page.wait_for_selector(".event-container", timeout=15000)

        event_links = await page.query_selector_all(".event-container a")
        print(f"🔗 Found {len(event_links)} events on calendar")

        for el in event_links:
            try:
                async with contextlib.asynccontextmanager(browser.new_page)() as detail_page:
                    href = await el.get_attribute("href")
                    full_url = f"https://library.nnva.gov{href}" if href else None
                    if not full_url:
                        continue

                    print(f"📅 Visiting event: {full_url}")
                    await detail_page.goto(full_url, timeout=30000)
                    html = await detail_page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    title = soup.select_one(".calendarTitle")
                    title = title.get_text(strip=True) if title else "Untitled Event"

                    date_tag = soup.select_one(".calendarDate")
                    raw_date = date_tag.get_text(strip=True) if date_tag else ""
                    event_date, month, day, year = format_date_from_text(raw_date)

                    time_tag = soup.select_one(".calendarTime")
                    time = time_tag.get_text(strip=True) if time_tag else "All Day Event"

                    location_tag = soup.select_one(".calendarLocation")
                    location = location_tag.get_text(strip=True) if location_tag else ""

                    desc_tag = soup.select_one(".calendarDescription")
                    description = desc_tag.get_text("\n\n", strip=True) if desc_tag else ""

                    events.append({
                        "Event Name": title,
                        "Event Link": full_url,
                        "Event Status": "Available",
                        "Time": time,
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
                print(f"⚠️ Failed to process event: {e}")

        await browser.close()

    print(f"✅ Scraped {len(events)} NNPL events.")
    return events


if __name__ == "__main__":
    asyncio.run(scrape_nnpl_events())
