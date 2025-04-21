import json
from unittest.mock import patch


class TestFlaskAuthEndpoints:
    def test_login_invalid_data(self, client):
        response = client.post('/login', json={
            'email': 'invalid',
            'password': ''
        })
        assert response.status_code == 400

    @patch('auth.service.AuthService.validate_refresh_token')
    def test_refresh_success(self, mock_validate, client, test_user):
        mock_validate.return_value = test_user
        response = client.post('/refresh', json={
            'refresh_token': 'valid' * 20
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data

    @patch('auth.service.AuthService.validate_refresh_token', return_value=None)
    def test_refresh_expired_token(self, mock_validate, client):
        response = client.post('/refresh', json={
            'refresh_token': 'expired' * 20
        })
        assert response.status_code == 401

    @patch('auth.service.AuthService.validate_refresh_token', return_value=None)
    def test_refresh_invalid_token(self, mock_validate, client):
        response = client.post('/refresh', json={
            'refresh_token': 'invalid' * 20
        })
        assert response.status_code == 401

    def test_refresh_invalid_data(self, client):
        response = client.post('/refresh', json={
            'refresh_token': ''
        })
        assert response.status_code == 400
