# src/scrapers/mercadolivre.py

import json
import re
from typing import Any

from .base import BaseScraper, PriceResult


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)

        s = str(v).strip()
        s = s.replace("R$", "").strip()

        # converte "4.299,90" -> "4299.90"
        if "," in s and s.count(",") == 1:
            s = s.replace(".", "").replace(",", ".")

        return float(s)
    except Exception:
        return None


def _extract_jsonld_objects(html: str) -> list[dict[str, Any]]:
    """
    Extrai todos os blocos JSON-LD do HTML.
    """
    results = []
    for match in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                results.append(data)
            elif isinstance(data, list):
                results.extend([x for x in data if isinstance(x, dict)])
        except Exception:
            continue
    return results


def _find_product_jsonld(objs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for obj in objs:
        t = obj.get("@type")
        if t == "Product" or (isinstance(t, list) and "Product" in t):
            return obj
    return None


def _extract_og_image(html: str) -> str | None:
    match = re.search(
        r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
        html,
        re.I,
    )
    if match:
        return match.group(1)
    return None


class MercadoLivreScraper(BaseScraper):
    site = "mercadolivre"

    async def fetch(self, page, url: str) -> PriceResult:
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Espera JSON-LD aparecer
        try:
            await page.wait_for_selector("script[type='application/ld+json']", timeout=15000)
        except Exception:
            pass

        await page.wait_for_timeout(1500)

        html = await page.content()

        title = None
        seller = None
        price = None
        shipping = None
        available = True
        image_url = None
        raw_debug = None

        # --- 1️⃣ JSON-LD ---
        jsonlds = _extract_jsonld_objects(html)
        product = _find_product_jsonld(jsonlds)

        if product:
            title = product.get("name")

            # imagem
            img = product.get("image")
            if isinstance(img, str):
                image_url = img
            elif isinstance(img, list) and img:
                image_url = img[0]

            offers = product.get("offers")
            if isinstance(offers, dict):
                offers = [offers]
            elif not isinstance(offers, list):
                offers = []

            best_price = None
            best_offer = None

            for offer in offers:
                p = _safe_float(offer.get("price"))
                if p is None:
                    continue
                if best_price is None or p < best_price:
                    best_price = p
                    best_offer = offer

            price = best_price

            if best_offer:
                raw_debug = json.dumps(best_offer, ensure_ascii=False)[:2000]

                availability = best_offer.get("availability")
                if isinstance(availability, str):
                    available = "InStock" in availability or "LimitedAvailability" in availability

                seller_info = best_offer.get("seller")
                if isinstance(seller_info, dict):
                    seller = seller_info.get("name")

        # --- 2️⃣ Fallback imagem via og:image ---
        if not image_url:
            image_url = _extract_og_image(html)

        # --- 3️⃣ Fallback preço via seletor ---
        if price is None:
            try:
                fraction = page.locator("span.andes-money-amount__fraction").first
                cents = page.locator("span.andes-money-amount__cents").first

                if await fraction.count() > 0:
                    frac_txt = (await fraction.inner_text()).strip()
                    cents_txt = (await cents.inner_text()).strip() if await cents.count() > 0 else "00"
                    price = _safe_float(f"{frac_txt},{cents_txt}")
                    raw_debug = f"fallback_selectors={frac_txt},{cents_txt}"
            except Exception:
                pass

        # --- 4️⃣ Fallback regex ---
        if price is None:
            match = re.search(r'R\$\s*([\d\.]+,\d{2})', html)
            if match:
                price = _safe_float(match.group(1))
                raw_debug = f"fallback_regex={match.group(0)}"

        # --- 5️⃣ Fallback título ---
        if not title:
            try:
                title = await page.locator("h1").first.inner_text()
            except Exception:
                pass

        return PriceResult(
            title=title,
            seller=seller,
            price=price,
            shipping=shipping,
            available=bool(available),
            image_url=image_url,
            raw=raw_debug,
        )