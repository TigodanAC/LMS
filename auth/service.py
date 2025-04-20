from datetime import datetime, timedelta
import bcrypt
from database.session import SessionLocal
from database.auth_queries import AuthQueries


class AuthService:
    def __init__(self):
        self.db = SessionLocal()
        self.queries = AuthQueries(self.db)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def authenticate_user(self, email: str, password: str):
        user = self.queries.get_user_by_email(email)
        if not user or not self.verify_password(password, user.password):
            return None
        return user

    def create_refresh_token_record(self, token: str, user_id: str, expires_delta: int):
        expires_at = datetime.utcnow() + timedelta(seconds=expires_delta)
        self.queries.delete_refresh_tokens(user_id=user_id)
        return self.queries.create_refresh_token(token, user_id, expires_at)

    def validate_refresh_token(self, token: str):
        normalized_token = token.replace('\n', '').strip()
        db_token = self.queries.get_refresh_token(normalized_token)
        if not db_token:
            print(f"Token not found in DB: {normalized_token[:50]}...")
            return None

        if datetime.utcnow() > db_token.expires_at:
            self.queries.delete_refresh_tokens(token=normalized_token)
            print("Token expired")
            return None

        self.queries.delete_refresh_tokens(user_id=db_token.user_id, token=normalized_token)
        return db_token.user

    def __del__(self):
        self.db.close()
