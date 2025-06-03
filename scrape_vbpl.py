import asyncio
from playwright.async_api import async_playwright, TimeoutError
import re

def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()'\"/-]", "", text)

async def scrape():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        page = await browser.new_page()

        print("🚀 Starting scrape...")
        await page.goto("https://vbpl.librarymarket.com/events/month")

        try:
            await page.click(".ui-dialog-titlebar-close", timeout=5000)
            print("✅ Popup closed.")
        except:
            print("⚠️ Popup already dismissed.")

        await page.wait_for_selector("article.event-card")
        cards = await page.locator("article.event-card").all()
        print(f"🔍 Found {len(cards)} event cards.")

        detail_page = await browser.new_page()

        for i, card in enumerate(cards[:50]):  # 🔒 Limit to 50 cards max for stability
            try:
                name = await card.locator("a.lc-event__link").inner_text(timeout=5000)
                link_suffix = await card.locator("a.lc-event__link").get_attribute("href", timeout=5000)
                link = f"https://vbpl.librarymarket.com{link_suffix}"
                status = await card.locator(".lc-core--extra-field span").inner_text(timeout=3000)
                time_slot = await card.locator(".lc-event-info-item--time").inner_text(timeout=3000)
                ages = await card.locator(".lc-event-info__item--colors").inner_text(timeout=3000)
                location = await card.locator(".lc-event__branch").inner_text(timeout=3000)
            except TimeoutError:
                print(f"⚠️ Timeout on card {i}")
                continue
            except Exception as e:
                print(f"⚠️ Error parsing card {i}: {e}")
                continue

            try:
                await detail_page.goto(link, timeout=10000)

                try:
                    description = await detail_page.locator(".field--name-body .field-item").inner_text(timeout=5000)
                except:
                    description = ""

                try:
                    month = await detail_page.locator(".lc-date-icon__item--month").inner_text(timeout=3000)
                    day = await detail_page.locator(".lc-date-icon__item--day").inner_text(timeout=3000)
                    year = await detail_page.locator(".lc-date-icon__item--year").inner_text(timeout=3000)
                except:
                    month, day, year = "", "", ""
            except Exception as e:
                print(f"⚠️ Detail page failed for card {i}: {e}")
                continue

            results.append({
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
            })

            await page.wait_for_timeout(500)  # ⏳ Prevent browser from crashing

        await detail_page.close()
        await browser.close()
        print(f"📦 {len(results)} events scraped.")
        return results

if __name__ == "__main__":
    asyncio.run(scrape())
