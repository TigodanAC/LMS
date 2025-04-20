import pytest
import json
from course.app import app
from database.models import Course

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def student_auth_headers():
    return {
        'Authorization': 'Bearer student_token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def teacher_auth_headers():
    return {
        'Authorization': 'Bearer teacher_token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def other_teacher_course(db):
    course = Course(
        name="Other Teacher Course",
        lector_id="other_teacher_id"
    )
    db.session.add(course)
    db.session.commit()
    return course


class TestRolePermissions:
    def test_student_cannot_create_course(self, client, student_auth_headers):
        response = client.post(
            "/courses",
            data=json.dumps({
                "name": "Unauthorized Course",
                "lector_id": "lector123",
                "groups": []
            }),
            headers=student_auth_headers
        )
        assert response.status_code == 403

    def test_teacher_cannot_access_other_courses(self, client, teacher_auth_headers, other_teacher_course):
        response = client.get(
            f"/courses/{other_teacher_course.id}",
            headers=teacher_auth_headers
        )
        assert response.status_code == 403
