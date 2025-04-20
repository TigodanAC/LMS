import pytest
from datetime import timedelta
from auth.service import AuthService
from database.models import User
from exceptions import InvalidCredentialsError, TokenExpiredError


class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService()

    def test_successful_login(self, auth_service, test_user):
        tokens = auth_service.login(test_user.email, "correct_password")
        assert "access_token" in tokens
        assert "refresh_token" in tokens

    def test_login_with_wrong_password(self, auth_service, test_user):
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(test_user.email, "wrong_password")

    def test_token_refresh(self, auth_service, test_user):
        tokens = auth_service.login(test_user.email, "correct_password")
        new_token = auth_service.refresh_token(tokens["refresh_token"])
        assert "access_token" in new_token

    def test_expired_token_refresh(self, auth_service, test_user):
        tokens = auth_service.login(test_user.email, "correct_password", expires_in=timedelta(seconds=-1))
        with pytest.raises(TokenExpiredError):
            auth_service.refresh_token(tokens["refresh_token"])
