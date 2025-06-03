import asyncio
from playwright.async_api import async_playwright

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://vbpl.librarymarket.com/events/month")

        # Close the library selector popup (X button)
        try:
            await page.click(".ui-dialog-titlebar-close", timeout=5000)
            print("✅ Popup closed.")
        except:
            print("⚠️ Popup not found or already closed.")

        await page.wait_for_selector("a.lc-event__link", timeout=10000)

        titles = await page.locator("a.lc-event__link").all_inner_texts()
        times = await page.locator("div.lc-event-info-item--time").all_inner_texts()

        count = min(len(titles), len(times))
        print(f"\n📅 Found {count} events:\n" + "=" * 40)
        for i in range(count):
            print(f"📌 {titles[i]}\n🕒 {times[i]}\n" + "-" * 40)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
