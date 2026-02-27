# src/scrapers/base.py
from dataclasses import dataclass

@dataclass
class PriceResult:
    title: str | None
    seller: str | None
    price: float | None
    shipping: float | None
    available: bool
    image_url: str | None
    raw: str | None

class BaseScraper:
    site: str = "base"

    async def fetch(self, page, url: str) -> PriceResult:
        raise NotImplementedError