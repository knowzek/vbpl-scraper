import asyncio
from playwright.async_api import async_playwright
import re


def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()'\"/-]", "", text)


async def scrape():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        page = await browser.new_page()

        await page.goto("https://vbpl.librarymarket.com/events/month", timeout=30000)

        # Close library selector popup
        try:
            await page.click(".ui-dialog-titlebar-close", timeout=5000)
            print("✅ Popup closed.")
        except:
            print("⚠️ Popup already dismissed or not found.")

        try:
            await page.wait_for_selector("a.lc-event__link", timeout=10000)
        except:
            print("❌ Event selector not found.")
            await browser.close()
            return results

        # Get event cards
        event_cards = await page.locator("article.event-card").all()
        print(f"🔍 Found {len(event_cards)} event cards.")

        for card in event_cards:
            try:
                name = await card.locator("a.lc-event__link").inner_text()
                link_suffix = await card.locator("a.lc-event__link").get_attribute("href")
                link = f"https://vbpl.librarymarket.com{link_suffix}"
                status = await card.locator("div.lc-core--extra-field span").inner_text()
                time_slot = await card.locator("div.lc-event-info-item--time").inner_text()
                ages = await card.locator("div.lc-event-info__item--colors").inner_text()
                location = await card.locator("div.lc-event__branch").inner_text()
            except:
                continue

            # Visit event detail page
            detail_page = await browser.new_page()
            try:
                await detail_page.goto(link, timeout=15000)

                try:
                    description = await detail_page.locator(".field--name-body .field-item").inner_text()
                except:
                    description = ""

                try:
                    month = await detail_page.locator(".lc-date-icon__item--month").inner_text()
                    day = await detail_page.locator(".lc-date-icon__item--day").inner_text()
                    year = await detail_page.locator(".lc-date-icon__item--year").inner_text()
                except:
                    month, day, year = "", "", ""

                record = {
                    "Event Name": remove_emojis(name.strip()),
                    "Event Link": link,
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
            finally:
                await detail_page.close()

        await browser.close()
        return results


if __name__ == "__main__":
    asyncio.run(scrape())
