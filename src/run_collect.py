# src/run_collect.py
import asyncio
from pathlib import Path

import yaml
from playwright.async_api import async_playwright

from src.db import init_db, insert_row
from src.scrapers.mercadolivre import MercadoLivreScraper

# Mapa de scrapers (vai crescer conforme você adicionar Amazon/Magalu/etc.)
SCRAPERS = {
    "mercadolivre": MercadoLivreScraper(),
}

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def run_once():
    cfg = load_config()
    targets = cfg.get("targets", [])

    Path("debug").mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()

        for t in targets:
            site = str(t.get("site", "")).strip()
            url = str(t.get("url", "")).strip()

            if not site or not url:
                print("[SKIP] alvo inválido no config.yaml:", t)
                continue

            scraper = SCRAPERS.get(site)
            if not scraper:
                print("[SKIP] scraper não cadastrado:", site)
                continue

            print("Coletando:", site, url)

            try:
                res = await scraper.fetch(page, url)

                # Debug quando vier vazio
                if res.price is None or res.title is None:
                    await page.screenshot(path=f"debug/{site}.png", full_page=True)
                    Path(f"debug/{site}.html").write_text(await page.content(), encoding="utf-8")
                    print(f"[DEBUG] URL final: {page.url}")
                    print(f"[DEBUG] Salvei debug/{site}.png e debug/{site}.html")

                # Print útil para você validar se pegou imagem
                print("Imagem capturada:", res.image_url)

                insert_row(
                    site=site,
                    url=url,
                    title=res.title,
                    seller=res.seller,
                    price=res.price,
                    shipping=res.shipping,
                    available=res.available,
                    image_url=res.image_url,
                    raw=res.raw,
                )

                print(f"[OK] {site} | {res.price} | {res.title}")

            except Exception as e:
                # salva evidências do erro
                try:
                    await page.screenshot(path=f"debug/{site}_error.png", full_page=True)
                except Exception:
                    pass

                Path(f"debug/{site}_error.txt").write_text(str(e), encoding="utf-8")

                insert_row(
                    site=site,
                    url=url,
                    title=None,
                    seller=None,
                    price=None,
                    shipping=None,
                    available=False,
                    image_url=None,
                    raw=f"ERROR: {e}",
                )

                print(f"[ERRO] {site} | {e}")

        await browser.close()

if __name__ == "__main__":
    init_db()
    asyncio.run(run_once())