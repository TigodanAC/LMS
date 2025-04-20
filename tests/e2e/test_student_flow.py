import pytest
import json
from course.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def student_user_creds():
    return {
        "email": "student@example.com",
        "password": "student_pass"
    }


@pytest.fixture
def auth_headers(client, student_user_creds):
    login_resp = client.post(
        "/login",
        data=json.dumps(student_user_creds),
        content_type='application/json'
    )
    tokens = json.loads(login_resp.data)
    return {
        'Authorization': f"Bearer {tokens['access_token']}",
        'Content-Type': 'application/json'
    }


class TestStudentFlow:
    def test_full_student_flow(self, client, auth_headers):
        courses_resp = client.get(
            "/courses",
            headers=auth_headers
        )
        courses = json.loads(courses_resp.data)

        test_resp = client.post(
            f"/test_results/{courses['data'][0]['tests'][0]['id']}",
            data=json.dumps([{"id": 1, "answer": ["A"]}]),
            headers=auth_headers
        )

        sop_resp = client.post(
            "/sop",
            data=json.dumps({
                "courses": [{
                    "course_id": courses["data"][0]["course_id"],
                    "blocks": [{
                        "block_type": "course",
                        "questions_answers": [{
                            "question": "How was the course?",
                            "question_type": "rating",
                            "answer": 5
                        }]
                    }]
                }]
            }),
            headers=auth_headers
        )

        assert courses_resp.status_code == 200
        assert len(courses["data"]) > 0
        assert test_resp.status_code == 201
        assert sop_resp.status_code == 200
