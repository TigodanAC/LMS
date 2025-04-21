from datetime import datetime, timedelta


class TestAuthQueries:
    def test_get_user_by_email(self, auth_queries, mock_db_session, test_user):
        mock_db_session.query().filter().first.return_value = test_user
        result = auth_queries.get_user_by_email("test@example.com")
        assert result == test_user

    def test_create_refresh_token(self, auth_queries, mock_db_session, test_user):
        token = "new_token"
        expires_at = datetime.utcnow() + timedelta(days=7)
        result = auth_queries.create_refresh_token(token, test_user.user_id, expires_at)
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    def test_get_refresh_token(self, auth_queries, mock_db_session, valid_refresh_token):
        mock_db_session.query().filter().first.return_value = valid_refresh_token
        result = auth_queries.get_refresh_token("valid_refresh_token")
        assert result == valid_refresh_token

    def test_delete_refresh_tokens_by_user(self, auth_queries, mock_db_session):
        auth_queries.delete_refresh_tokens(user_id="user123")
        assert mock_db_session.query().filter().delete.called
        assert mock_db_session.commit.called

    def test_delete_refresh_tokens_by_token(self, auth_queries, mock_db_session):
        auth_queries.delete_refresh_tokens(token="token123")
        assert mock_db_session.query().filter().delete.called
        assert mock_db_session.commit.called
