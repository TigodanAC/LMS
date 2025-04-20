import pytest
import json


class TestCoursesAPI:
    def test_get_courses_pagination(self, client, admin_auth_headers):
        response = client.get(
            '/courses?limit=5&offset=0',
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert len(data['data']) <= 5

    def test_create_course_permissions(self, client, admin_auth_headers, student_auth_headers):
        course_data = {
            "name": "New Course",
            "description": "Description",
            "lector_id": "lector123",
            "groups": [{"group_id": "group1", "seminarist_id": "semi123"}]
        }

        response = client.post(
            '/courses',
            data=json.dumps(course_data),
            headers=admin_auth_headers
        )
        assert response.status_code == 201

        response = client.post(
            '/courses',
            data=json.dumps(course_data),
            headers=student_auth_headers
        )
        assert response.status_code == 403

    def test_get_course_details(self, client, admin_auth_headers, test_course):
        response = client.get(
            f'/courses/{test_course.id}',
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['course_id'] == test_course.id
        assert 'name' in data
        assert 'description' in data
