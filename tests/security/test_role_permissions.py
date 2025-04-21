# tests/security/test_role_permissions.py
import pytest
import json
from course.app import app
from database.models import Course, User, Block, Unit, Test, Group, Set, SetBlock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime


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
def other_teacher_user(db_session):
    user = User(
        user_id="other_teacher123",
        email="other_teacher@example.com",
        role="teacher",
        password="hashed_password",
        first_name="Other",
        last_name="Teacher"
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
def test_course(db_session, teacher_user):
    course = Course(
        course_id="course123",
        name="Test Course",
        lector_id=teacher_user.user_id
    )
    db_session.add(course)

    group = Group(
        group_id="group123",
        course_id=course.course_id,
        seminarist_id=teacher_user.user_id
    )
    db_session.add(group)

    db_session.commit()
    return course


@pytest.fixture
def other_teacher_course(db_session, other_teacher_user):
    course = Course(
        course_id="other_course123",
        name="Other Teacher Course",
        lector_id=other_teacher_user.user_id
    )
    db_session.add(course)

    group = Group(
        group_id="other_group123",
        course_id=course.course_id,
        seminarist_id=other_teacher_user.user_id
    )
    db_session.add(group)

    db_session.commit()
    return course


@pytest.fixture
def test_block(db_session, test_course):
    block = Block(
        block_id="block123",
        course_id=test_course.course_id,
        name="Test Block"
    )
    db_session.add(block)
    db_session.commit()
    return block


@pytest.fixture
def test_unit(db_session, test_block):
    unit = Unit(
        unit_id=1,
        block_id=test_block.block_id,
        course_id=test_block.course_id,
        name="Test Unit",
        type="lecture",
        content="Test content"
    )
    db_session.add(unit)
    db_session.commit()
    return unit


@pytest.fixture
def test_test(db_session):
    test = Test(
        test_id="test123",
        questions=json.dumps([{"id": 1, "text": "Q1", "type": "single"}]),
        answers=json.dumps([{"id": 1, "answer": ["A"]}])
    )
    db_session.add(test)
    db_session.commit()
    return test


@pytest.fixture
def test_sop(db_session, student_user, test_course):
    sop_set = Set(
        set_id="set123",
        user_id=student_user.user_id,
        creation_time=datetime.now()
    )
    db_session.add(sop_set)

    sop_block = SetBlock(
        set_id=sop_set.set_id,
        course_id=test_course.course_id,
        type="lecturer",
        user_id=student_user.user_id,
        content=json.dumps({
            "teacher_id": test_course.lector_id,
            "questions_answers": [{
                "question": "Q1",
                "type": "rating",
                "answer": 5
            }]
        })
    )
    db_session.add(sop_block)

    db_session.commit()
    return sop_set


@pytest.fixture
def admin_token(admin_user):
    return "admin_token"


@pytest.fixture
def teacher_token(teacher_user):
    return "teacher_token"


@pytest.fixture
def other_teacher_token(other_teacher_user):
    return "other_teacher_token"


@pytest.fixture
def student_token(student_user):
    return "student_token"


@pytest.fixture
def admin_headers(admin_token):
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def teacher_headers(teacher_token):
    return {
        "Authorization": f"Bearer {teacher_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def other_teacher_headers(other_teacher_token):
    return {
        "Authorization": f"Bearer {other_teacher_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def student_headers(student_token):
    return {
        "Authorization": f"Bearer {student_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestRolePermissions:
    def test_student_cannot_create_course(self, client, student_headers):
        response = client.post(
            "/courses",
            json={
                "name": "Unauthorized Course",
                "lector_id": "lector123",
                "groups": []
            },
            headers=student_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_create_course(self, client, teacher_headers):
        response = client.post(
            "/courses",
            json={
                "name": "Unauthorized Course",
                "lector_id": "lector123",
                "groups": []
            },
            headers=teacher_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_access_other_courses(self, client, teacher_headers, other_teacher_course):
        response = client.get(
            f"/courses/{other_teacher_course.course_id}",
            headers=teacher_headers
        )
        assert response.status_code == 401

    def test_student_cannot_update_course(self, client, student_headers, test_course):
        response = client.put(
            f"/courses/{test_course.course_id}",
            json={"name": "Updated Name"},
            headers=student_headers
        )
        assert response.status_code == 401

    def test_student_cannot_create_block(self, client, student_headers, test_course):
        response = client.post(
            f"/courses/{test_course.course_id}/blocks",
            json={"name": "New Block"},
            headers=student_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_create_block_in_other_course(self, client, teacher_headers, other_teacher_course):
        response = client.post(
            f"/courses/{other_teacher_course.course_id}/blocks",
            json={"name": "New Block"},
            headers=teacher_headers
        )
        assert response.status_code == 401

    def test_student_cannot_create_unit(self, client, student_headers, test_block):
        response = client.post(
            f"/blocks/{test_block.block_id}/units",
            json={
                "name": "New Unit",
                "type": "lecture",
                "content": "Content"
            },
            headers=student_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_create_unit_in_other_block(self, client, teacher_headers, other_teacher_course):
        block = Block(
            block_id="other_block123",
            course_id=other_teacher_course.course_id,
            name="Other Block"
        )
        response = client.post(
            f"/blocks/{block.block_id}/units",
            json={
                "name": "New Unit",
                "type": "lecture",
                "content": "Content"
            },
            headers=teacher_headers
        )
        assert response.status_code == 401

    def test_student_cannot_create_test(self, client, student_headers):
        response = client.post(
            "/tests",
            json={
                "questions": [{"id": 1, "text": "Q1", "type": "single"}],
                "answers": [{"id": 1, "answer": ["A"]}]
            },
            headers=student_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_view_other_teacher_sop_results(self, client, teacher_headers, other_teacher_user):
        response = client.get(
            f"/sop/teacher_results?teacher_id={other_teacher_user.user_id}",
            headers=teacher_headers
        )
        assert response.status_code == 401

    def test_student_cannot_view_teacher_sop_results(self, client, student_headers):
        response = client.get(
            "/sop/teacher_results",
            headers=student_headers
        )
        assert response.status_code == 401

    def test_student_cannot_view_course_students(self, client, student_headers, test_course):
        response = client.get(
            f"/courses/{test_course.course_id}/students",
            headers=student_headers
        )
        assert response.status_code == 401

    def test_teacher_cannot_view_other_course_students(self, client, teacher_headers, other_teacher_course):
        response = client.get(
            f"/courses/{other_teacher_course.course_id}/students",
            headers=teacher_headers
        )
        assert response.status_code == 401
