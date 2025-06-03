import asyncio
from playwright.async_api import async_playwright
import re

def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()'\"/-]", "", text)

async def scrape():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        await page.goto("https://vbpl.librarymarket.com/events/month")

        # Close the popup if it's visible
        try:
            await page.click(".ui-dialog-titlebar-close", timeout=5000)
            print("✅ Popup closed.")
        except:
            print("⚠️ Popup already dismissed or not present.")

        # Wait for event links to load
        await page.wait_for_selector("a.lc-event__link", timeout=10000)
        event_links = await page.query_selector_all("a.lc-event__link")

        print(f"🔍 Found {len(event_links)} event links...")

        for link_el in event_links:
            try:
                name = await link_el.inner_text()
                href = await link_el.get_attribute("href")
                full_link = f"https://vbpl.librarymarket.com{href}"

                # Open event detail page
                detail_page = await browser.new_page()
                await detail_page.goto(full_link)

                # Extract additional data
                try:
                    description = await detail_page.locator(".field--name-body .field-item").inner_text()
                except:
                    description = ""

                try:
                    status = await detail_page.locator("div.lc-core--extra-field span").inner_text()
                except:
                    status = ""

                try:
                    time_slot = await detail_page.locator("div.lc-event-info-item--time").inner_text()
                except:
                    time_slot = ""

                try:
                    ages = await detail_page.locator("div.lc-event-info__item--colors").inner_text()
                except:
                    ages = ""

                try:
                    location = await detail_page.locator("div.lc-event__branch").inner_text()
                except:
                    location = ""

                try:
                    month = await detail_page.locator(".lc-date-icon__item--month").inner_text()
                    day = await detail_page.locator(".lc-date-icon__item--day").inner_text()
                    year = await detail_page.locator(".lc-date-icon__item--year").inner_text()
                except:
                    month, day, year = "", "", ""

                await detail_page.close()

                record = {
                    "Event Name": remove_emojis(name.strip()),
                    "Event Link": full_link,
                    "Event Status": remove_emojis(status.strip()),
                    "Time": remove_emojis(time_slot.strip()),
                    "Ages": remove_emojis(ages.strip()),
                    "Location": remove_emojis(location.strip()),
                    "Month": month.strip(),
                    "Day": day.strip(),
                    "Year": year.strip(),
                    "Event Description": remove_emojis(description.strip())
                }

                results.append(record)
            except Exception as e:
                print(f"❌ Error scraping an event: {e}")
                continue

        await browser.close()
        return results

if __name__ == "__main__":
    asyncio.run(scrape())
