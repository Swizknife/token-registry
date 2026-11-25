import datetime as dt

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total_tokens: int
    completed: int
    avg_wait_seconds: float | None
    avg_service_seconds: float | None
    throughput_per_hour: float | None


class CounterEfficiencyRow(BaseModel):
    counter_id: int
    counter_name: str
    completed: int
    avg_service_seconds: float | None


class TimeseriesBucket(BaseModel):
    bucket_start: dt.datetime
    service_category: str
    arrivals: int
    completions: int
    avg_service_seconds: float | None
