from pydantic import BaseModel, ConfigDict, Field


class CompetitorCreate(BaseModel):
    name: str
    source_type: str = "mock"
    url: str | None = None
    shop_name: str | None = None
    image_url: str | None = None
    price_selector: str | None = None
    promo_selector: str | None = None
    manual_price: float | None = Field(default=None, gt=0)
    manual_promo: str | None = None
    mock_prices: list[float] = []
    mock_promos: list[str] = []
    active: bool = True


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    name: str
    source_type: str
    url: str | None
    shop_name: str | None
    image_url: str | None
    price_selector: str | None
    promo_selector: str | None
    manual_price: float | None
    manual_promo: str | None
    mock_index: int
    active: bool
