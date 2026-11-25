import datetime as dt

from pydantic import BaseModel, field_validator

SERVICE_CATEGORIES = [
    "General Enquiry",
    "Document Verification",
    "Application Submission",
    "Payment",
    "Technical Support",
    "Other",
]


class TokenCreateRequest(BaseModel):
    phone_number: str
    service_category: str

    @field_validator("service_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in SERVICE_CATEGORIES:
            raise ValueError(f"service_category must be one of {SERVICE_CATEGORIES}")
        return v


class TokenCreateResponse(BaseModel):
    token_id: int
    token_number: str
    service_category: str
    status: str
    registration_time: dt.datetime
    estimated_wait_time: int | None = None
    queue_url: str


class TokenStaffRow(BaseModel):
    token_id: int
    token_number: str
    phone_masked: str
    service_category: str
    status: str
    registration_time: dt.datetime
    called_time: dt.datetime | None = None
    counter_id: int | None = None
    estimated_wait_time: int | None = None

    model_config = {"from_attributes": True}


class TokenDetail(BaseModel):
    token_id: int
    token_number: str
    phone_number: str
    service_category: str
    status: str
    registration_time: dt.datetime
    called_time: dt.datetime | None = None
    service_start_time: dt.datetime | None = None
    completion_time: dt.datetime | None = None
    counter_id: int | None = None
    recall_count: int
    estimated_wait_time: int | None = None

    model_config = {"from_attributes": True}
