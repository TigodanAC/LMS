from unittest.mock import MagicMock, patch


class TestCourseService:
    def test_get_student_courses_info(self, course_service, mock_queries):
        mock_queries.get_student_courses_info.return_value = ([{"course_id": "course1"}], 1)
        result, total = course_service.get_student_courses_info("user1")
        assert len(result) == 1

    def test_get_all_courses_info(self, course_service, mock_queries):
        mock_queries.get_all_courses_info.return_value = ([{"course_id": "course1"}], 1)
        result, total = course_service.get_all_courses_info()
        assert len(result) == 1

    def test_get_course_details_student(self, course_service, mock_queries):
        mock_queries.get_course_details.return_value = {"course_id": "course1"}
        with patch.object(course_service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = MagicMock(user_id="student1")
            result = course_service.get_course_details("course1", "student1")
            assert result["course_id"] == "course1"

    def test_submit_sop_invalid_data(self, course_service):
        result = course_service.submit_sop("user1", {})
        assert result["status"] == 400

    def test_get_teacher_sop_results(self, course_service, mock_queries):
        mock_queries.get_teacher_sop_results.return_value = {"data": [], "status": 200}
        result = course_service.get_teacher_sop_results("teacher1", "teacher")
        assert result["status"] == 200

    def test_get_course_sop_results(self, course_service, mock_queries):
        mock_queries.get_course_sop_results.return_value = {"data": {}, "status": 200}
        result = course_service.get_course_sop_results("course1", "user1", "teacher")
        assert result["status"] == 200

    def test_verify_test_access_admin(self, course_service):
        result = course_service.verify_test_access("admin1", "admin", "test1")
        assert result is None

    def test_submit_test_results(self, course_service, mock_queries):
        mock_queries.submit_test_results.return_value = [{"id": 1, "is_right": True}]
        result = course_service.submit_test_results("user1", "test1", [{"id": 1, "answer": ["A"]}])
        assert isinstance(result, list)

    def test_get_test_or_results(self, course_service, mock_queries):
        mock_queries.get_test_or_results.return_value = {"data": {}, "status": 200}
        result = course_service.get_test_or_results("user1", "test1")
        assert result["status"] == 200

    def test_create_course_success(self, course_service, mock_queries):
        mock_queries.get_user_by_id.return_value = MagicMock(role="teacher")
        mock_queries.create_course.return_value = {"status": 201}

        result = course_service.create_course("Math", "Math course", "lector1",
                                              [{"group_id": "group1", "seminarist_id": "teacher1"}])
        assert result["status"] == 201

    def test_create_block_success(self, course_service, mock_queries):
        mock_queries.create_block.return_value = {"status": 201}
        result = course_service.create_block("course1", "Block 1", "user1", "teacher")
        assert result["status"] == 201
