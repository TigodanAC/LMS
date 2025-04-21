import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from database.models import User, RefreshToken, Base
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database import session as session_module

os.environ['JWT_PRIVATE_KEY_FILE'] = 'tests/configs/test_signature.pem'
os.environ['JWT_PUBLIC_KEY_FILE'] = 'tests/configs/test_signature.pub'

from auth.app import app
from course.service import CourseService
from database.course_queries import CourseQueries
from database.session import SessionLocal


@pytest.fixture
def mock_db_session():
    return MagicMock(spec=SessionLocal)


@pytest.fixture
def course_queries(mock_db_session):
    return CourseQueries(mock_db_session)


@pytest.fixture
def valid_access_token(mock_token):
    return mock_token


@pytest.fixture
def admin_access_token(mock_admin_token):
    return mock_admin_token


@pytest.fixture
def teacher_access_token(mock_teacher_token):
    return mock_teacher_token


@pytest.fixture
def mock_queries():
    return MagicMock(spec=CourseQueries)


@pytest.fixture
def course_service(mock_queries):
    service = CourseService()
    service.queries = mock_queries
    return service


@pytest.fixture
def mock_token():
    return "valid_token"


@pytest.fixture
def mock_admin_token():
    return "admin_token"


@pytest.fixture
def mock_teacher_token():
    return "teacher_token"


@pytest.fixture
def test_user():
    hashed_password = bcrypt.hashpw("correct_password".encode('utf-8'), bcrypt.gensalt())
    user = User(
        user_id="user123",
        email="test@example.com",
        password=hashed_password.decode('utf-8'),
        first_name="Test",
        last_name="User",
        role="student"
    )
    return user


@pytest.fixture
def valid_refresh_token(test_user):
    return RefreshToken(
        token="valid_refresh_token",
        user_id=test_user.user_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )


@pytest.fixture
def expired_refresh_token(test_user):
    return RefreshToken(
        token="expired_refresh_token",
        user_id=test_user.user_id,
        expires_at=datetime.utcnow() - timedelta(days=1)
    )


@pytest.fixture
def auth_queries(mock_db_session):
    from database.auth_queries import AuthQueries
    return AuthQueries(mock_db_session)


@pytest.fixture
def auth_service(mock_db_session):
    with patch('auth.service.SessionLocal', return_value=mock_db_session):
        from auth.service import AuthService
        service = AuthService()
        service.verify_password = lambda p, h: p == "correct_password"
        return service


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with patch('course.app.decode_jwt') as mock_decode:
        mock_decode.return_value = {
            'user_id': 'test_user',
            'role': 'admin',
            'exp': datetime.now().timestamp() + 3600
        }
        with app.test_client() as client:
            yield client


@pytest.fixture
def course_client(mock_db_session, setup_database):
    from course.app import app as course_app
    with patch('database.session.SessionLocal', return_value=mock_db_session):
        course_app.config['TESTING'] = True
        with course_app.test_client() as client:
            yield client


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_module.SessionLocal = sessionmaker(bind=engine)
    yield
