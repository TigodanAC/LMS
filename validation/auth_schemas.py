from pydantic import BaseModel, Field, EmailStr
from .validators import BaseValidationModel, validate_email
from .enums import RoleEnum
from pydantic import validator
from typing import Optional


class LoginRequest(BaseValidationModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)

    _email_validator = validator('email')(validate_email)


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

    _email_validator = validator('email')(validate_email)
