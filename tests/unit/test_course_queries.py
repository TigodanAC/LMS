from unittest.mock import MagicMock
import json


class TestCourseQueries:
    def test_validate_student_id_valid(self, course_queries, mock_db_session):
        mock_db_session.query().filter().first.return_value = MagicMock()
        assert course_queries.validate_student_id("valid_student_id") is True

    def test_validate_student_id_invalid(self, course_queries, mock_db_session):
        mock_db_session.query().filter().first.return_value = None
        assert course_queries.validate_student_id("invalid_student_id") is False

    def test_determine_teacher_role(self, course_queries, mock_db_session):
        mock_user = MagicMock(role="teacher")
        mock_db_session.query().filter().first.return_value = mock_user
        assert course_queries.determine_teacher_role("teacher_id") == "teacher"

    def test_is_course_lector_true(self, course_queries, mock_db_session):
        mock_db_session.query().filter().first.return_value = MagicMock()
        assert course_queries.is_course_lector("course_id", "lector_id") is True

    def test_is_course_seminarist_true(self, course_queries, mock_db_session):
        mock_db_session.query().filter().first.return_value = MagicMock()
        assert course_queries.is_course_seminarist("course_id", "seminarist_id") is True

    def test_get_course_details_admin(self, course_queries, mock_db_session):
        mock_course = MagicMock(course_id="course1", name="Math", description="Math course", lector_id="lector1")
        mock_db_session.query().filter().first.return_value = mock_course
        mock_db_session.query().join().filter().all.return_value = [MagicMock(user_id="seminarist1")]

        result = course_queries.get_course_details("course1", "admin_id", "admin")
        assert result["course_id"] == "course1"

    def test_submit_sop_success(self, course_queries, mock_db_session):
        mock_db_session.query().filter().order_by().first.return_value = None
        mock_db_session.query().filter().all.return_value = []

        sop_data = [{
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

        result = course_queries.submit_sop("user1", sop_data)
        assert result["status"] == 201

    def test_get_teacher_sop_results(self, course_queries, mock_db_session):
        mock_block = MagicMock(
            content=json.dumps({
                "teacher_id": "teacher1",
                "questions_answers": [{
                    "question": "Q1",
                    "type": "rating",
                    "answer": 5
                }]
            }),
            course_id="course1",
            type="lecturer"
        )
        mock_db_session.query().filter().all.return_value = [mock_block]

        result = course_queries.get_teacher_sop_results("teacher1", "teacher")
        assert len(result["data"]) > 0

    def test_create_test_success(self, course_queries, mock_db_session):
        questions = [{"id": 1, "text": "Q1", "type": "single"}]
        answers = [{"id": 1, "answer": ["A"]}]

        result = course_queries.create_test("test1", questions, answers)
        assert result["status"] == 201

    def test_create_block_success(self, course_queries, mock_db_session):
        mock_db_session.query().filter().all.return_value = []

        result = course_queries.create_block("block1_course1", "course1", "Block 1")
        assert result["status"] == 201

    def test_create_unit_success(self, course_queries, mock_db_session):
        mock_db_session.query().scalar.return_value = 0

        result = course_queries.create_unit("block1", "course1", "Unit 1", "lecture", "Content")
        assert result["status"] == 201
