import pytest
from database.database import db as _db
from course.app import app


@pytest.fixture(scope='session')
def app():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture
def admin_auth_headers():
    return {
        'Authorization': 'Bearer admin_token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def student_auth_headers():
    return {
        'Authorization': 'Bearer student_token',
        'Content-Type': 'application/json'
    }
