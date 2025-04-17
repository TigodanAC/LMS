from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union
from database.session import SessionLocal
from database.course_queries import CourseQueries


class CourseService:
    def __init__(self):
        self.db = SessionLocal()
        self.queries = CourseQueries(self.db)

    def validate_student_id(self, student_id: str) -> bool:
        return self.queries.validate_student_id(student_id)

    def determine_teacher_role(self, teacher_id: str) -> str:
        return self.queries.determine_teacher_role(teacher_id)

    def get_student_courses_info(
            self,
            user_id: str,
            search: str = '',
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[Dict], int]:
        return self.queries.get_student_courses_info(
            user_id=user_id,
            search=search,
            limit=limit,
            offset=offset
        )

    def get_all_courses_info(
            self,
            search: str = '',
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[Dict], int]:
        return self.queries.get_all_courses_info(
            search=search,
            limit=limit,
            offset=offset
        )

    def get_course_details(self, course_id: str, user_id: str) -> Optional[Dict]:
        return self.queries.get_course_details(course_id, user_id)

    def submit_sop(self, user_id: str, sop_data: List[Dict]) -> Dict:
        if not sop_data or not isinstance(sop_data, list):
            return {"error": "Invalid SOP data format", "status": 400}

        for course_data in sop_data:
            if "course_id" not in course_data or "blocks" not in course_data:
                return {"error": "Missing required fields in SOP data", "status": 400}

            for block in course_data["blocks"]:
                if "block_type" not in block or "questions_answers" not in block:
                    return {"error": "Missing required fields in block data", "status": 400}

                if block["block_type"] in ["lecturer", "seminarist"] and "teacher_id" not in block:
                    return {"error": "Teacher ID required for this block type", "status": 400}

        return self.queries.submit_sop(user_id, sop_data)

    def get_teacher_sop_results(self, teacher_id: str, user_role: str) -> Dict:
        return self.queries.get_teacher_sop_results(teacher_id, user_role)

    def get_course_sop_results(self, course_id: str, current_user_id: str, current_user_role: str) -> Dict:
        return self.queries.get_course_sop_results(course_id, current_user_id, current_user_role)

    def get_unit_by_id(self, unit_id: int, user_id: str) -> Optional[Dict]:
        return self.queries.get_unit_by_id(unit_id, user_id)

    def verify_test_access(self, user_id: str, user_role: str, test_id: str) -> Optional[Dict]:
        if user_role == "admin":
            return None
        access_granted = self.queries.check_test_access(user_id, user_role, test_id)
        if not access_granted:
            return {"error": "Access denied to this test", "status": 403}
        return None

    def submit_test_results(self, user_id: str, test_id: str, user_answers: List[Dict]) -> Dict:
        return self.queries.submit_test_results(user_id, test_id, user_answers)

    def get_test_or_results(self, user_id: str, test_id: str) -> Dict:
        return self.queries.get_test_or_results(user_id, test_id)

    def get_student_test_results(self, teacher_id: str, teacher_role: str, test_id: str, student_id: str) -> Union[
        Dict, List]:
        access_error = self.queries.verify_teacher_access(teacher_id, teacher_role, test_id)
        if access_error:
            return access_error
        return self.queries.get_student_test_results(test_id, student_id)

    def check_user_exists(self, user_id: str) -> bool:
        return self.queries.check_user_exists(user_id)

    def update_student_test_results(self, teacher_id: str, teacher_role: str,
                                 test_id: str, student_id: str, results_data: List[Dict]) -> Dict:
        if not self.queries.check_user_exists(student_id):
            return {"error": "User not found", "status": 404}
        access_error = self.queries.verify_teacher_access(teacher_id, teacher_role, test_id)
        if access_error:
            return access_error
        return self.queries.update_test_results(test_id, student_id, results_data)

    def update_unit_content(self, teacher_id: str, teacher_role: str,
                            unit_id: int, new_content: Union[str, dict]) -> Dict:
        unit = self.queries.get_unit(unit_id)
        if not unit:
            return {"error": "Unit not found", "status": 404}

        access_error = self.queries.verify_teacher_access_to_course(
            teacher_id, teacher_role, unit.course_id
        )
        if access_error:
            return access_error
        return self.queries.update_unit_content(unit_id, new_content)

    def create_test(self, questions: List[Dict], answers: List[Dict], deadline: Optional[str] = None) -> Dict:
        new_test_id = self.queries.generate_test_id()
        return self.queries.create_test(
            test_id=new_test_id,
            questions=questions,
            answers=answers,
            deadline=deadline
        )

    def __del__(self):
        self.db.close()
