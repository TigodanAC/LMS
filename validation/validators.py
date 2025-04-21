from pydantic import validator, BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


def validate_future_date(cls, v: Optional[datetime]) -> Optional[datetime]:
    if v and v <= datetime.now():
        raise ValueError("Date must be in the future")
    return v


def validate_sop_score(cls, v: int) -> int:
    if not 1 <= v <= 5:
        raise ValueError("SOP score must be between 1 and 5")
    return v


def validate_email(v: str) -> str:
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("Invalid email format")
    return v.lower()


class BaseValidationModel(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
