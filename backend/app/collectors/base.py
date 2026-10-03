from dataclasses import dataclass

@dataclass
class CollectResult:
    success: bool
    price: float | None
    promo_text: str | None = None
    raw: str = ""
    error: str | None = None
