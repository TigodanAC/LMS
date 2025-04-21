from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic import field_validator
from typing import Optional
from .validators import BaseValidationModel, validate_email
from .enums import RoleEnum


class LoginRequest(BaseValidationModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()


class RefreshRequest(BaseValidationModel):
    refresh_token: str = Field(..., min_length=50)


class TokenPayload(BaseValidationModel):
    email: str
    user_id: str
    role: RoleEnum
    exp: int
    type: Optional[str] = None

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class TokenResponse(BaseValidationModel):
    access_token: str
    refresh_token: Optional[str] = None


class UserResponse(BaseValidationModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    role: RoleEnum
    group_id: Optional[str]


class UserCreateRequest(BaseValidationModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    role: RoleEnum
    group_id: Optional[str]

    @field_validator('email')
    def validate_email(cls, v):
        return validate_email(v)
