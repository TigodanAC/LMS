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

    def delete_refresh_tokens(self, user_id: str = None, token: str = None):
        query = self.db.query(RefreshToken)

        if user_id:
            query = query.filter(RefreshToken.user_id == user_id)

        if token:
            normalized_token = token.replace('\n', '').strip()
            query = query.filter(RefreshToken.token != normalized_token)

        query.delete()
        self.db.commit()
