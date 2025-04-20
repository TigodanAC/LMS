from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union
from database.session import SessionLocal
from database.course_queries import CourseQueries
from database.models import User


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

    def get_course(self, course_id: str):
        return self.queries.get_course(course_id)

    def get_course_details(self, course_id: str, user_id: str) -> Optional[Dict]:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        return self.queries.get_course_details(course_id, user_id, user.role)

    def submit_sop(self, user_id: str, sop_data: Dict) -> Dict:
        if not sop_data or "courses" not in sop_data:
            return {"error": "Invalid SOP data format", "status": 400}

        for course in sop_data["courses"]:
            if "course_id" not in course or "blocks" not in course:
                return {"error": "Missing required fields in course data", "status": 400}

            for block in course["blocks"]:
                if "block_type" not in block or "questions_answers" not in block:
                    return {"error": "Missing required fields in block data", "status": 400}

                if block["block_type"] in ["lecturer", "seminarist"] and "teacher_id" not in block:
                    return {"error": "Teacher ID required for this block type", "status": 400}

                for question in block["questions_answers"]:
                    if question["question_type"] == "rating" and "answer" not in question:
                        return {"error": "Missing answer for rating question", "status": 400}
                    elif question["question_type"] == "text" and "text_answer" not in question:
                        return {"error": "Missing text answer for text question", "status": 400}

        return self.queries.submit_sop(user_id, sop_data["courses"])

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

    def create_test(self, questions: List[Dict], answers: List[Dict], deadline: Optional[datetime] = None) -> Dict:
        new_test_id = self.queries.generate_test_id()
        return self.queries.create_test(
            test_id=new_test_id,
            questions=questions,
            answers=answers,
            deadline=deadline
        )

    def create_course(self, name: str, description: str, lector_id: str, groups: List[Dict]) -> Dict:
        lecturer = self.queries.get_user_by_id(lector_id)
        if not lecturer or lecturer.role != "teacher":
            return {"error": "Invalid lecturer ID or not a teacher", "status": 400}

        for group in groups:
            if 'group_id' not in group or 'seminarist_id' not in group:
                return {"error": "Each group must have group_id and seminarist_id", "status": 400}

            seminarist = self.queries.get_user_by_id(group['seminarist_id'])
            if not seminarist or seminarist.role != "teacher":
                return {"error": f"Invalid seminarist ID {group['seminarist_id']} or not a teacher", "status": 400}

        try:
            course_id = self.queries.generate_course_id()
            return self.queries.create_course(
                course_id=course_id,
                name=name,
                description=description,
                lector_id=lector_id,
                groups=groups
            )
        except Exception as e:
            print(f"Error creating course: {e}")
            return {"error": "Failed to create course", "status": 500}

    def is_course_lector(self, course_id: str, user_id: str) -> bool:
        return self.queries.is_course_lector(course_id, user_id)

    def update_course(self, course_id: str, user_role: str, user_id: str, update_data: Dict) -> Dict:
        if 'lector_id' in update_data and user_role != "admin":
            return {"error": "Only admin can change course lector", "status": 403}

        if 'lector_id' in update_data and user_role == "admin":
            new_lector = self.queries.get_user_by_id(update_data['lector_id'])
            if not new_lector or new_lector.role != "teacher":
                return {"error": "Invalid lector ID or not a teacher", "status": 400}

        if 'groups' in update_data:
            for group in update_data['groups']:
                seminarist = self.queries.get_user_by_id(group['seminarist_id'])
                if not seminarist or seminarist.role != "teacher":
                    return {"error": f"Invalid seminarist ID {group['seminarist_id']} or not a teacher", "status": 400}

        try:
            return self.queries.update_course(
                course_id=course_id,
                user_role=user_role,
                update_data=update_data
            )
        except Exception as e:
            print(f"Error updating course: {e}")
            return {"error": "Failed to update course", "status": 500}

    def is_course_lector_or_seminarist(self, course_id: str, user_id: str) -> bool:
        return self.queries.is_course_lector_or_seminarist(course_id, user_id)

    def is_block_lector_or_seminarist(self, block_id: str, user_id: str) -> bool:
        block_info = self.queries.get_query_block(block_id)
        if not block_info or isinstance(block_info, dict):
            return False
        return self.queries.is_course_lector_or_seminarist(block_info.course_id, user_id)

    def create_block(self, course_id: str, name: str, user_id: str, user_role: str) -> Dict:
        course = self.queries.get_course_by_id(course_id)
        if not course:
            return {"error": "Course not found", "status": 404}

        block_id = self.queries.generate_block_id(course_id)

        try:
            return self.queries.create_block(
                block_id=block_id,
                course_id=course_id,
                name=name
            )
        except Exception as e:
            print(f"Error creating block: {e}")
            return {"error": "Failed to create block", "status": 500}

    def get_block(self, block_id: str, user_id: str, user_role: str) -> Dict:
        block_data = self.queries.get_query_block(block_id)
        if isinstance(block_data, dict) and 'error' in block_data:
            return block_data

        return {
            "block_id": block_data.block_id,
            "name": block_data.name,
            "units": [unit.unit_id for unit in block_data.units] if hasattr(block_data, 'units') else [],
            "status": 200
        }

    def update_block(self, block_id: str, name: str, user_id: str, user_role: str) -> Dict:
        try:
            return self.queries.update_block(
                block_id=block_id,
                name=name
            )
        except Exception as e:
            print(f"Error updating block: {e}")
            return {"error": "Failed to update block", "status": 500}

    def is_student_in_block_course(self, block_id: str, student_id: str) -> bool:
        block_info = self.queries.get_query_block(block_id)
        if not block_info or isinstance(block_info, dict):
            return False
        return self.queries.is_student_in_course(block_info.course_id, student_id)

    def is_unit_lector_or_seminarist(self, unit_id: int, user_id: str) -> bool:
        return self.queries.is_unit_lector_or_seminarist(unit_id, user_id)

    def is_unit_accessible_to_student(self, unit_id: int, user_id: str) -> bool:
        return self.queries.is_unit_accessible_to_student(unit_id, user_id)

    def create_unit(self, block_id: str, name: str, unit_type: str, content: Union[str, dict],
                    user_id: str, user_role: str) -> Dict:
        block = self.queries.get_query_block(block_id)
        if not block:
            return {"error": "Block not found", "status": 404}

        try:
            return self.queries.create_unit(
                block_id=block_id,
                course_id=block.course_id,
                name=name,
                unit_type=unit_type,
                content=content
            )
        except Exception as e:
            print(f"Error creating unit: {e}")
            return {"error": "Failed to create unit", "status": 500}

    def update_unit(self, unit_id: int, update_data: Dict, user_id: str, user_role: str) -> Dict:
        try:
            return self.queries.update_unit(
                unit_id=unit_id,
                update_data=update_data
            )
        except Exception as e:
            print(f"Error updating unit: {e}")
            return {"error": "Failed to update unit", "status": 500}

    def get_course_students(
            self,
            course_id: str,
            user_id: str,
            user_role: str,
            limit: int = 20,
            offset: int = 0,
            search: str = ''
    ) -> Dict:
        if user_role not in ["admin", "teacher"]:
            return {"error": "Access denied", "status": 403}

        try:
            if user_role == "teacher":
                is_lector = self.queries.is_course_lector(course_id, user_id)
                is_seminarist = self.queries.is_course_seminarist(course_id, user_id)

                if not is_lector and not is_seminarist:
                    return {"error": "Access denied - not your course", "status": 403}

            return self.queries.get_course_students(
                course_id=course_id,
                user_id=user_id,
                user_role=user_role,
                limit=limit,
                offset=offset,
                search=search
            )
        except Exception as e:
            print(f"Error in get_course_students: {e}")
            return {"error": "Internal server error", "status": 500}

    def __del__(self):
        self.db.close()
