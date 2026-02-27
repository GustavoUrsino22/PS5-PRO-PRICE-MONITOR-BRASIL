import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from src.scrapers.mercadolivre import MercadoLivreScraper

URL = "https://www.mercadolivre.com.br/console-ps5-pro-sony-playstation-5-pro-2tb-digital-novo-cnf/up/MLBU3477178538#polycard_client=search-desktop&search_layout=grid&position=25&type=product&tracking_id=fa69786d-d155-4175-8ced-7adcc2d0d7cf&wid=MLB5773615266&sid=search"

async def main():
    scraper = MercadoLivreScraper()
    Path("debug").mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # importante p/ debug
        context = await browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        print("URL final:", page.url)
        print("Title:", await page.title())

        # salva HTML e screenshot para ver o que realmente carregou
        html = await page.content()
        Path("debug/page.html").write_text(html, encoding="utf-8")
        await page.screenshot(path="debug/page.png", full_page=True)

        # roda o scraper
        res = await scraper.fetch(page, page.url)
        print(res)

        await browser.close()

asyncio.run(main())