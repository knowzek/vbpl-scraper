import asyncio
from playwright.async_api import async_playwright
import re


def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()'\"/-]", "", text)


async def scrape():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://vbpl.librarymarket.com/events/month")

        # Close library selector popup
        try:
            await page.click(".ui-dialog-titlebar-close", timeout=5000)
            print("✅ Popup closed.")
        except:
            print("⚠️ Popup already dismissed.")

        await page.wait_for_selector("article.event-card")
        event_cards = await page.locator("article.event-card").all()
        print(f"🔍 Found {len(event_cards)} event cards.")

        for card in event_cards:
            try:
                name = await card.locator("a.lc-event__link").inner_text()
                link_suffix = await card.locator("a.lc-event__link").get_attribute("href")
                link = f"https://vbpl.librarymarket.com{link_suffix}"

                status_node = card.locator(".lc-registration-label")
                status = await status_node.inner_text() if await status_node.count() > 0 else "Unknown"

                time_node = card.locator(".lc-event-info-item--time")
                time_slot = await time_node.inner_text() if await time_node.count() > 0 else ""

                ages_node = card.locator(".lc-event-info__item--colors, .lc-event__age-groups span")
                ages = await ages_node.inner_text() if await ages_node.count() > 0 else ""

                location_node = card.locator(".lc-event__branch")
                location = await location_node.inner_text() if await location_node.count() > 0 else ""

                # Visit event detail page
                detail_page = await browser.new_page()
                await detail_page.goto(link)

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

                await detail_page.close()

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
                print(f"✅ Scraped: {name.strip()}")

            except Exception as e:
                print(f"⚠️ Error parsing card: {e}")
                continue

        await browser.close()
        return results


if __name__ == "__main__":
    asyncio.run(scrape())
