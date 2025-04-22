import pytest
from datetime import datetime
from unittest.mock import patch
from course.app import app
from database.models import Course, User, Block, Unit, Test, TestResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope='function')
def db_session():
    engine = create_engine('sqlite:///:memory:')
    from database.models import Base
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def admin_user(db_session):
    user = User(
        user_id="admin123",
        email="admin@example.com",
        role="admin",
        password="hashed_password",
        first_name="Admin",
        last_name="User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def teacher_user(db_session):
    user = User(
        user_id="teacher123",
        email="teacher@example.com",
        role="teacher",
        password="hashed_password",
        first_name="Teacher",
        last_name="User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def student_user(db_session):
    user = User(
        user_id="student123",
        email="student@example.com",
        role="student",
        password="hashed_password",
        first_name="Student",
        last_name="User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def other_teacher_user(db_session):
    user = User(
        user_id="other_teacher123",
        email="other_teacher@example.com",
        role="teacher",
        password="hashed_password",
        first_name="Other teacher",
        last_name="User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_course(db_session, teacher_user):
    course = Course(
        course_id="course123",
        name="Test Course",
        lector_id=teacher_user.user_id
    )
    db_session.add(course)
    db_session.commit()
    return course


@pytest.fixture
def admin_token(admin_user):
    return "admin_token"


@pytest.fixture
def teacher_token(teacher_user):
    return "teacher_token"


@pytest.fixture
def student_token(student_user):
    return "student_token"


@pytest.fixture
def admin_headers():
    return {
        "Authorization": "Bearer admin_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def teacher_headers():
    return {
        "Authorization": "Bearer teacher_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def student_headers():
    return {
        "Authorization": "Bearer student_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestCourseEndpoints:
    def test_create_course_as_admin(self, client, db_session, admin_headers):
        with patch('course.app.decode_jwt') as mock_decode:
            mock_decode.return_value = {
                'user_id': 'admin123',
                'role': 'admin',
                'exp': datetime.now().timestamp() + 3600
            }

            response = client.post(
                "/courses",
                json={
                    "name": "New Course",
                    "description": "Course Description",
                    "lector_id": "teacher123",
                    "groups": [{"group_id": "group1", "seminarist_id": "teacher123"}]
                },
                headers=admin_headers
            )

        assert response.status_code == 201

    def test_get_courses_as_student(self, client, db_session, student_headers, test_course):
        response = client.get(
            "/courses",
            headers=student_headers
        )
        assert response.status_code == 200

    def test_update_course_as_teacher(self, client, db_session, teacher_headers, test_course):
        response = client.put(
            f"/courses/{test_course.course_id}",
            json={"name": "Updated Course Name"},
            headers=teacher_headers
        )
        assert response.status_code == 201

    def test_create_block_as_teacher(self, client, db_session, teacher_headers, test_course):
        response = client.post(
            f"/courses/{test_course.course_id}/blocks",
            json={"name": "New Block"},
            headers=teacher_headers
        )
        assert response.status_code == 201

    def test_create_unit_in_block(self, client, db_session, teacher_headers, test_course):
        block = Block(
            block_id="block123",
            course_id=test_course.course_id,
            name="Test Block"
        )
        db_session.add(block)
        db_session.commit()

        response = client.post(
            f"/blocks/{block.block_id}/units",
            json={
                "name": "New Unit",
                "type": "lecture",
                "content": "Unit content"
            },
            headers=teacher_headers
        )
        assert response.status_code == 201

    def test_get_sop_results(self, client, db_session, teacher_headers, test_course):
        response = client.get(
            f"/sop/course_results/{test_course.course_id}",
            headers=teacher_headers
        )
        assert response.status_code == 200

    def test_get_course_students(self, client, db_session, teacher_headers, test_course, student_user):
        response = client.get(
            f"/courses/{test_course.course_id}/students",
            headers=teacher_headers
        )
        assert response.status_code == 200
