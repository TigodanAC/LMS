from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.models import Course, Group, User, Block, Unit, Set, SetBlock, Test, TestResult
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from flask import json
from collections import OrderedDict


class CourseQueries:
    def __init__(self, db: Session):
        self.db = db

    def get_student_courses_info(
            self,
            user_id: str,
            search: str = '',
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[Dict], int]:
        student = self.db.query(User).filter(User.user_id == user_id).first()
        if not student or not student.group_id:
            return [], 0

        query = self.db.query(Course, Group.seminarist_id) \
            .join(Group, Course.course_id == Group.course_id) \
            .filter(Group.group_id == student.group_id)

        if search:
            query = query.filter(
                or_(
                    Course.name.ilike(f"%{search}%"),
                    Course.description.ilike(f"%{search}%")
                )
            )

        total = query.count()
        results = query.offset(offset).limit(limit).all()

        course_list = []
        for course, seminarist_id in results:
            lector = self.db.query(User) \
                .filter(User.user_id == course.lector_id) \
                .first()

            seminarist = self.db.query(User) \
                .filter(User.user_id == seminarist_id) \
                .first()

            course_data = {
                "course_id": course.course_id,
                "course_name": course.name,
                "description": course.description,
                "lector": {
                    "lector_id": course.lector_id,
                    "first_name": lector.first_name if lector else "",
                    "last_name": lector.last_name if lector else ""
                },
                "seminarist": {
                    "seminarist_id": seminarist_id,
                    "first_name": seminarist.first_name if seminarist else "",
                    "last_name": seminarist.last_name if seminarist else ""
                } if seminarist else None
            }
            course_list.append(course_data)

        return course_list, total

    def get_course_details(self, course_id: str, user_id: str) -> Optional[Dict]:
        student = self.db.query(User).filter(User.user_id == user_id).first()
        if not student or not student.group_id:
            return None

        course = self.db.query(Course) \
            .join(Group, Course.course_id == Group.course_id) \
            .filter(Group.group_id == student.group_id,
                    Course.course_id == course_id) \
            .first()

        if not course:
            return None

        lector = self.db.query(User) \
            .filter(User.user_id == course.lector_id) \
            .first()

        blocks = self.db.query(Block).filter(Block.course_id == course_id).order_by(Block.block_id).all()
        type_order = {'lecture': 0, 'seminar': 1, 'test': 2}

        course_data = {
            "course_id": str(course.course_id),
            "name": course.name,
            "description": course.description,
            "lector": {
                "lector_id": str(course.lector_id),
                "first_name": lector.first_name if lector else None,
                "last_name": lector.last_name if lector else None
            },
            "blocks": []
        }

        for block in blocks:
            units = self.db.query(Unit) \
                .filter(Unit.block_id == block.block_id,
                        Unit.course_id == course_id) \
                .all()

            sorted_units = sorted(units, key=lambda u: (type_order[u.type], u.name))

            block_data = {
                "block_id": str(block.block_id),
                "name": block.name,
                "units": [{
                    "unit_id": f"{unit.block_id}_{unit.course_id}",
                    "name": unit.name,
                    "type": unit.type
                } for unit in sorted_units]
            }
            course_data["blocks"].append(block_data)

        return course_data

    def submit_sop(self, user_id: str, sop_data: List[Dict]) -> Dict:
        last_submission = self.db.query(Set) \
            .filter(Set.user_id == user_id) \
            .order_by(Set.creation_time.desc()) \
            .first()

        if last_submission and (datetime.utcnow() - last_submission.creation_time) < timedelta(days=30):
            return {
                "error": "You have already filled out the current version of SOP",
                "status": 409
            }

        set_ids = [s[0] for s in self.db.query(Set.set_id).filter(Set.user_id == user_id).all()]

        if set_ids:
            self.db.query(SetBlock) \
                .filter(SetBlock.set_id.in_(set_ids)) \
                .delete(synchronize_session=False)

            self.db.query(Set) \
                .filter(Set.user_id == user_id) \
                .delete(synchronize_session=False)

        try:
            new_set = Set(
                user_id=user_id,
                creation_time=datetime.utcnow()
            )
            self.db.add(new_set)
            self.db.flush()

            for course_data in sop_data:
                course_id = course_data["course_id"]
                blocks = course_data["blocks"]

                for block in blocks:
                    content = OrderedDict()
                    content["teacher_id"] = block.get("teacher_id")
                    content["questions_answers"] = block.get("questions_answers", [])

                    set_block = SetBlock(
                        set_id=new_set.set_id,
                        course_id=course_id,
                        type=block["block_type"],
                        user_id=user_id,
                        content=json.dumps(content, ensure_ascii=False, sort_keys=False)
                    )
                    self.db.add(set_block)

            self.db.commit()
            return {
                "message": "SOP submitted successfully",
                "status": 201
            }

        except Exception as e:
            self.db.rollback()
            print(f"Error submitting SOP: {e}")
            return {
                "error": "Failed to submit SOP",
                "status": 500
            }

    def get_teacher_sop_results(self, teacher_id: str, user_role: str) -> Dict:
        if user_role not in ["lecturer", "seminarist"]:
            return {
                "error": "Only lecturers and seminarists can view teacher SOP results",
                "status": 403
            }

        block_type = "lecturer" if user_role == "lecturer" else "seminarist"
        sop_blocks = self.db.query(SetBlock) \
            .filter(
            SetBlock.type == block_type,
            SetBlock.content.like(f'%"teacher_id": "{teacher_id}"%')
        ) \
            .all()

        if not sop_blocks:
            return {
                "message": "No SOP results found for this teacher",
                "status": 404
            }

        question_stats = {}

        for block in sop_blocks:
            try:
                content = eval(block.content)
                qa_pairs = content.get("questions_answers", [])

                for qa in qa_pairs:
                    question = qa["question"]
                    answer = qa["answer"]

                    if question not in question_stats:
                        question_stats[question] = {}

                    if answer not in question_stats[question]:
                        question_stats[question][answer] = 0

                    question_stats[question][answer] += 1
            except:
                continue

        results = []
        for question, answers in question_stats.items():
            answer_distribution = []
            for answer, count in sorted(answers.items()):
                answer_distribution.append({
                    "answer": answer,
                    "count": count
                })
            question_data = OrderedDict()
            question_data["question"] = question
            question_data["answers"] = answer_distribution
            results.append(question_data)

        return {
            "data": results,
            "status": 200
        }

    def get_course_sop_results(self, course_id: str, current_user_id: str, current_user_role: str) -> Dict:
        if current_user_role not in ["lecturer", "admin"]:
            return {
                "error": "Only lecturers and admins can view course SOP results",
                "status": 403
            }

        if current_user_role == "lecturer":
            course = self.db.query(Course) \
                .filter(
                Course.course_id == course_id,
                Course.lector_id == current_user_id
            ) \
                .first()
            if not course:
                return {
                    "error": "You can only view SOP for your own courses",
                    "status": 403
                }

        course = self.db.query(Course) \
            .filter(Course.course_id == course_id) \
            .first()

        if not course:
            return {
                "error": "Course not found",
                "status": 404
            }

        lector = self.db.query(User).filter(User.user_id == course.lector_id).first()

        course_block_results = self._get_block_results(course_id, "course")
        lector_results = self._get_block_results(course_id, "lecturer", course.lector_id)

        lector_data = {
            "lector_id": str(course.lector_id),
            "first_name": lector.first_name if lector else "",
            "last_name": lector.last_name if lector else "",
            "results": lector_results
        }

        seminarists = self.db.query(User) \
            .join(Group, User.user_id == Group.seminarist_id) \
            .filter(Group.course_id == course_id) \
            .all()

        seminarists_results = []
        for seminarist in seminarists:
            results = self._get_block_results(course_id, "seminarist", seminarist.user_id)
            seminarists_results.append({
                "seminarist_id": str(seminarist.user_id),
                "first_name": seminarist.first_name,
                "last_name": seminarist.last_name,
                "results": results
            })

        return {
            "data": {
                "course": {
                    "course_results": course_block_results,
                    "lector": lector_data,
                    "seminarists": seminarists_results
                }
            },
            "status": 200
        }

    def _get_block_results(self, course_id: str, block_type: str, teacher_id: str = None) -> List[Dict]:
        query = self.db.query(SetBlock) \
            .filter(
            SetBlock.course_id == course_id,
            SetBlock.type == block_type
        )

        if block_type in ["lecturer", "seminarist"] and teacher_id:
            query = query.filter(SetBlock.content.like(f'%"teacher_id": "{teacher_id}"%'))

        blocks = query.all()
        question_stats = {}

        for block in blocks:
            try:
                content = eval(block.content)
                qa_pairs = content.get("questions_answers", [])

                for qa in qa_pairs:
                    question = qa["question"]
                    answer = qa["answer"]

                    if question not in question_stats:
                        question_stats[question] = {}

                    if answer not in question_stats[question]:
                        question_stats[question][answer] = 0

                    question_stats[question][answer] += 1
            except:
                continue

        results = []
        for question, answers in question_stats.items():
            answer_distribution = []
            for answer, count in sorted(answers.items()):
                answer_distribution.append({
                    "answer": answer,
                    "count": count
                })
            results.append({
                "question": question,
                "answers": answer_distribution
            })

        return results

    def get_unit_by_id(self, unit_id: int, user_id: str) -> Optional[Dict]:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        unit = self.db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if not unit:
            return None

        if user.role == "admin":
            return self._format_unit_response(unit)

        if user.role in ["lecturer", "seminarist"]:
            if user.role == "lecturer":
                has_access = self.db.query(Course).filter(
                    Course.course_id == unit.course_id,
                    Course.lector_id == user_id
                ).first()
            else:
                has_access = self.db.query(Group).filter(
                    Group.course_id == unit.course_id,
                    Group.seminarist_id == user_id
                ).first()

            if has_access:
                return self._format_unit_response(unit)

        if user.role == "student" and user.group_id:
            has_access = self.db.query(Group).filter(
                Group.group_id == user.group_id,
                Group.course_id == unit.course_id
            ).first()
            if has_access:
                return self._format_unit_response(unit)

        return None

    def _format_unit_response(self, unit: Unit) -> Dict:
        return OrderedDict([
            ("name", unit.name),
            ("type", unit.type),
            ("content", unit.content)
        ])

    def check_test_access(self, user_id: str, user_role: str, test_id: str) -> bool:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False

        if user_role == "admin":
            return True

        unit = self.db.query(Unit).filter(
            Unit.type == "test",
            Unit.content.like(f'%"test_id": "{test_id}"%')
        ).first()
        if not unit:
            return False

        if user_role == "lecturer":
            course = self.db.query(Course).filter(
                Course.course_id == unit.course_id,
                Course.lector_id == user_id
            ).first()
            return course is not None

        if user_role == "seminarist":
            group = self.db.query(Group).filter(
                Group.course_id == unit.course_id,
                Group.seminarist_id == user_id
            ).first()
            return group is not None

        if user_role == "student" and user.group_id:
            group = self.db.query(Group).filter(
                Group.group_id == user.group_id,
                Group.course_id == unit.course_id
            ).first()
            return group is not None

        return False

    def submit_test_results(self, user_id: str, test_id: str, user_answers: List[Dict]) -> Dict:
        test = self.db.query(Test).filter(Test.test_id == test_id).first()
        if not test:
            return {"error": "Test not found", "status": 404}

        existing_result = self.db.query(TestResult).filter(
            TestResult.user_id == user_id,
            TestResult.test_id == test_id
        ).first()
        if existing_result:
            return {"error": "Test already completed", "status": 400}

        try:
            correct_answers = json.loads(test.answers)
        except (ValueError, TypeError):
            return {"error": "Invalid test answers format", "status": 500}

        correct_answers_dict = {str(item['id']): set(item['answer']) for item in correct_answers}

        results = []
        for user_answer in user_answers:
            question_id = str(user_answer['id'])
            user_answer_set = set(user_answer.get('answer', []))
            correct_answer_set = correct_answers_dict.get(question_id, set())
            is_right = user_answer_set == correct_answer_set

            results.append({
                "id": int(question_id),
                "is_right": is_right
            })

        try:
            test_result = TestResult(
                user_id=user_id,
                test_id=test_id,
                results=json.dumps(results, ensure_ascii=False)
            )
            self.db.add(test_result)
            self.db.commit()

            return {"data": results, "status": 201}

        except Exception as e:
            self.db.rollback()
            print(f"Error saving test results: {e}")
            return {"error": "Failed to save test results", "status": 500}

    def get_test_or_results(self, user_id: str, test_id: str) -> Dict:
        test_result = self.db.query(TestResult).filter(
            TestResult.user_id == user_id,
            TestResult.test_id == test_id
        ).first()

        if test_result:
            try:
                results = json.loads(test_result.results)
                formatted_results = []

                for result in results:
                    ordered_result = OrderedDict()
                    ordered_result["id"] = result.get("id")
                    ordered_result["is_right"] = result.get("is_right")
                    formatted_results.append(ordered_result)

                return {
                    "results": formatted_results,
                    "status": 200
                }
            except (ValueError, TypeError):
                return {"error": "Invalid results format", "status": 500}

        test = self.db.query(Test).filter(Test.test_id == test_id).first()
        if not test:
            return {"error": "Test not found", "status": 404}

        try:
            questions_raw = json.loads(test.questions)
            formatted_questions = []

            for question in questions_raw:
                ordered_question = OrderedDict()
                ordered_question["id"] = question.get("id")
                ordered_question["text"] = question.get("text")
                ordered_question["type"] = question.get("type")

                if "answers" in question:
                    ordered_question["answers"] = question["answers"]
                else:
                    ordered_question["answers"] = []

                formatted_questions.append(ordered_question)

            return {
                "data": formatted_questions,
                "status": 200
            }
        except (ValueError, TypeError):
            return {"error": "Invalid questions format", "status": 500}
