from sqlalchemy.orm import Session
from database.models import User, RefreshToken
import datetime


class AuthQueries:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create_refresh_token(self, token: str, user_id: str, expires_at: datetime.datetime):
        normalized_token = token.replace('\n', '').strip()
        db_token = RefreshToken(
            token=normalized_token,
            user_id=user_id,
            expires_at=expires_at
        )
        self.db.add(db_token)
        try:
            self.db.commit()
            return db_token
        except Exception as e:
            self.db.rollback()
            print(f"Failed to save refresh token: {str(e)}")
            raise

    def get_refresh_token(self, token: str):
        normalized_token = token.replace('\n', '').strip()
        return self.db.query(RefreshToken) \
            .filter(RefreshToken.token == normalized_token) \
            .first()

    def delete_refresh_token(self, token: str):
        normalized_token = token.replace('\n', '').strip()
        self.db.query(RefreshToken) \
            .filter(RefreshToken.token == normalized_token) \
            .delete()
        self.db.commit()
