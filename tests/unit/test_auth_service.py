from unittest.mock import MagicMock


def test_verify_password_correct(auth_service, test_user):
    assert auth_service.verify_password("correct_password", test_user.password)


def test_verify_password_incorrect(auth_service, test_user):
    assert not auth_service.verify_password("wrong_password", test_user.password)


def test_authenticate_user_success(auth_service, test_user):
    auth_service.queries.get_user_by_email = MagicMock(return_value=test_user)
    user = auth_service.authenticate_user("test@example.com", "correct_password")
    assert user == test_user


def test_authenticate_user_wrong_password(auth_service, test_user):
    auth_service.queries.get_user_by_email = MagicMock(return_value=test_user)
    user = auth_service.authenticate_user("test@example.com", "wrong_password")
    assert user is None


def test_authenticate_user_not_found(auth_service):
    auth_service.queries.get_user_by_email = MagicMock(return_value=None)
    user = auth_service.authenticate_user("nonexistent@example.com", "password")
    assert user is None


def test_create_refresh_token_record(auth_service):
    auth_service.queries.create_refresh_token = MagicMock()
    auth_service.queries.delete_refresh_tokens = MagicMock()

    auth_service.create_refresh_token_record("token123", "user123", 3600)

    auth_service.queries.delete_refresh_tokens.assert_called_once_with(user_id="user123")
    auth_service.queries.create_refresh_token.assert_called_once()


def test_validate_refresh_token_success(auth_service, test_user, valid_refresh_token):
    valid_refresh_token.user = test_user
    auth_service.queries.get_refresh_token = MagicMock(return_value=valid_refresh_token)
    auth_service.queries.delete_refresh_tokens = MagicMock()

    user = auth_service.validate_refresh_token("valid_refresh_token")
    assert user == test_user


def test_validate_refresh_token_expired(auth_service, expired_refresh_token):
    auth_service.queries.get_refresh_token = MagicMock(return_value=expired_refresh_token)
    auth_service.queries.delete_refresh_tokens = MagicMock()

    user = auth_service.validate_refresh_token("expired_refresh_token")
    assert user is None


def test_validate_refresh_token_not_found(auth_service):
    auth_service.queries.get_refresh_token = MagicMock(return_value=None)

    user = auth_service.validate_refresh_token("nonexistent_token")
    assert user is None
