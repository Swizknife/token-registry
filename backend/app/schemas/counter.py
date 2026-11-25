from pydantic import BaseModel


class CounterResponse(BaseModel):
    counter_id: int
    counter_name: str
    assigned_service: str | None = None
    current_token_id: int | None = None
    current_token_number: str | None = None
    counter_status: str

    model_config = {"from_attributes": True}


class CounterCreateRequest(BaseModel):
    counter_name: str
    assigned_service: str | None = None


class CallNextResponse(BaseModel):
    token_id: int
    token_number: str
    service_category: str
    counter_id: int
    counter_name: str
