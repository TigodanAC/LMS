import json


class TestFlaskCoursesEndpoints:
    def test_get_courses_student_success(self, course_client, valid_access_token):
        response = course_client.get(
            '/courses',
            headers={'Authorization': f'Bearer {valid_access_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data[0]["course_id"] == "course1"

    def test_create_course_admin_success(self, course_client, admin_access_token):
        data = {
            "name": "Math",
            "description": "Math course",
            "lector_id": "lector1",
            "groups": [{"group_id": "group1", "seminarist_id": "teacher1"}]
        }
        response = course_client.post(
            '/courses',
            json=data,
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        assert response.status_code == 201

    def test_get_course_details_success(self, course_client, valid_access_token):
        response = course_client.get(
            '/courses/course1',
            headers={'Authorization': f'Bearer {valid_access_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "Math"

    def test_update_course_teacher_success(self, course_client, teacher_access_token):
        data = {"name": "New Name"}
        response = course_client.put(
            '/courses/course1',
            json=data,
            headers={'Authorization': f'Bearer {teacher_access_token}'}
        )
        assert response.status_code == 200

    def test_submit_sop_success(self, course_client, valid_access_token):
        data = [{
            "course_id": "course1",
            "blocks": [{
                "block_type": "lecturer",
                "teacher_id": "teacher1",
                "questions_answers": [{
                    "question": "Q1",
                    "question_type": "rating",
                    "answer": 5
                }]
            }]
        }]
        response = course_client.post(
            '/sop',
            json=data,
            headers={'Authorization': f'Bearer {valid_access_token}'}
        )
        assert response.status_code == 201

    def test_get_teacher_sop_results(self, course_client, teacher_access_token):
        response = course_client.get(
            '/sop/teacher_results',
            headers={'Authorization': f'Bearer {teacher_access_token}'}
        )
        assert response.status_code == 200

    def test_create_test_success(self, course_client, teacher_access_token):
        data = {
            "questions": [{"id": 1, "text": "Q1", "type": "single"}],
            "answers": [{"id": 1, "answer": ["A"]}]
        }
        response = course_client.post(
            '/tests',
            json=data,
            headers={'Authorization': f'Bearer {teacher_access_token}'}
        )
        assert response.status_code == 201

    def test_submit_test_results(self, course_client, valid_access_token):
        data = [{"id": 1, "answer": ["A"]}]
        response = course_client.post(
            '/test_results/test1',
            json=data,
            headers={'Authorization': f'Bearer {valid_access_token}'}
        )
        assert response.status_code == 201

    def test_create_block_success(self, course_client, teacher_access_token):
        data = {"name": "Block 1"}
        response = course_client.post(
            '/courses/course1/blocks',
            json=data,
            headers={'Authorization': f'Bearer {teacher_access_token}'}
        )
        assert response.status_code == 201

    def test_create_unit_with_mocked_service(self):
        from course.app import app
        client = app.test_client()

        headers = {"Authorization": "Bearer faketoken"}
        payload = {
            "name": "Unit",
            "type": "text",
            "content": "Some content"
        }

        response = client.post(
            "/blocks/block123/units",
            headers=headers,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 201

    def test_get_course_students(self, course_client, teacher_access_token):
        response = course_client.get(
            '/courses/course1/students',
            headers={'Authorization': f'Bearer {teacher_access_token}'}
        )
        assert response.status_code == 200
