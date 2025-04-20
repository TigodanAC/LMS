import pytest
from course.service import CourseService
from exceptions import CourseNotFoundError, PermissionDeniedError


class TestCourseService:
    @pytest.fixture
    def service(self):
        return CourseService()

    def test_create_course(self, service, admin_user):
        course = service.create_course(
            admin_user,
            name="Math 101",
            description="Basic Mathematics",
            lector_id="lector123"
        )
        assert course.id is not None
        assert course.name == "Math 101"

    def test_get_course_for_student(self, service, student_user, test_course):
        course = service.get_course_for_user(test_course.id, student_user)
        assert course.id == test_course.id

    def test_get_nonexistent_course(self, service, admin_user):
        with pytest.raises(CourseNotFoundError):
            service.get_course_for_user("nonexistent", admin_user)
