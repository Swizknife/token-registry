from pydantic import BaseModel


class NowServingRow(BaseModel):
    counter_id: int
    counter_name: str
    token_number: str | None = None


class PublicDisplayResponse(BaseModel):
    now_serving: list[NowServingRow]
    upcoming: list[str]
    recently_completed: list[str]
