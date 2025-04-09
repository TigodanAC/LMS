from datetime import datetime
from typing import List, Optional, Dict, Tuple
from database.session import SessionLocal
from database.course_queries import CourseQueries


class CourseService:
    def __init__(self):
        self.db = SessionLocal()
        self.queries = CourseQueries(self.db)

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

    def __del__(self):
        self.db.close()
