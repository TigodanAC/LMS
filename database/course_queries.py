from sqlalchemy.orm import Session
from sqlalchemy import or_, func, select
from database.models import Course, Group, User, Block, Unit, Set, SetBlock, Test, TestResult
from typing import List, Optional, Dict, Tuple, Union
from datetime import datetime, timedelta
from flask import json
from collections import OrderedDict


class CourseQueries:
    def __init__(self, db: Session):
        self.db = db

    def validate_student_id(self, student_id: str) -> bool:
        student = self.db.query(User).filter(
            User.user_id == student_id,
            User.role == "student"
        ).first()
        return student is not None

    def determine_teacher_role(self, teacher_id: str) -> str:
        teacher = self.db.query(User).filter(
            User.user_id == teacher_id
        ).first()
        return teacher.role if teacher else None

    def _check_course_access(self, course_id: str, user_id: str) -> Dict[str, bool]:
        return {
            "is_lector": self.is_course_lector(course_id, user_id),
            "is_seminarist": self.is_course_seminarist(course_id, user_id)
        }

    def is_course_lector(self, course_id: str, user_id: str) -> bool:
        return self.db.query(Course).filter(
            Course.course_id == course_id,
            Course.lector_id == user_id
        ).first() is not None

    def is_course_seminarist(self, course_id: str, user_id: str) -> bool:
        return self.db.query(Group).filter(
            Group.course_id == course_id,
            Group.seminarist_id == user_id
        ).first() is not None

    def is_course_lector_or_seminarist(self, course_id: str, user_id: str) -> bool:
        access = self._check_course_access(course_id, user_id)
        return access["is_lector"] or access["is_seminarist"]

    def is_block_lector_or_seminarist(self, block_id: str, user_id: str) -> bool:
        block = self.get_query_block(block_id)
        if not block:
            return False
        return self.is_course_lector_or_seminarist(block.course_id, user_id)

    def is_unit_lector_or_seminarist(self, unit_id: int, user_id: str) -> bool:
        unit = self.db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if not unit:
            return False
        return self.is_course_lector_or_seminarist(unit.course_id, user_id)

    def verify_teacher_access(self, teacher_id: str, teacher_role: str, test_id: str) -> Optional[Dict]:
        test = self.db.query(Test).filter(Test.test_id == test_id).first()
        if not test:
            return {"error": "Test not found", "status": 404}

        unit = self.db.query(Unit).filter(
            Unit.content.contains(test_id),
            Unit.type == 'test'
        ).first()

        if not unit:
            return {"error": "Course not found for this test", "status": 404}

        if teacher_role == "teacher":
            access = self._check_course_access(unit.course_id, teacher_id)
            if not (access["is_lector"] or access["is_seminarist"]):
                return {"error": "Access denied - not your course", "status": 403}

        return None

    def get_course(self, course_id: str):
        return self.db.query(Course).filter(Course.course_id == course_id).first()

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

        if user_role == "teacher":
            is_lecturer = self.db.query(Course).filter(
                Course.course_id == unit.course_id,
                Course.lector_id == user_id
            ).first()

            is_seminarist = self.db.query(Group).filter(
                Group.course_id == unit.course_id,
                Group.seminarist_id == user_id
            ).first()

            return is_lecturer is not None or is_seminarist is not None

        if user_role == "student" and user.group_id:
            group = self.db.query(Group).filter(
                Group.group_id == user.group_id,
                Group.course_id == unit.course_id
            ).first()
            return group is not None

        return False

    def is_block_accessible_to_student(self, block_id: str, user_id: str) -> bool:
        student = self.db.query(User).filter(User.user_id == user_id).first()
        if not student or not student.group_id:
            return False

        block = self.db.query(Block).filter(Block.block_id == block_id).first()
        if not block:
            return False

        return self.db.query(Group).filter(
            Group.group_id == student.group_id,
            Group.course_id == block.course_id
        ).first() is not None

    def is_unit_accessible_to_student(self, unit_id: int, user_id: str) -> bool:
        student = self.db.query(User).filter(User.user_id == user_id).first()
        if not student or not student.group_id:
            return False

        unit = self.db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if not unit:
            return False

        return self.db.query(Group).filter(
            Group.group_id == student.group_id,
            Group.course_id == unit.course_id
        ).first() is not None

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

    def get_all_courses_info(
            self,
            search: str = '',
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[Dict], int]:
        query = self.db.query(Course)

        if search:
            query = query.filter(
                or_(
                    Course.name.ilike(f"%{search}%"),
                    Course.description.ilike(f"%{search}%")
                )
            )

        total = query.count()
        courses = query.offset(offset).limit(limit).all()

        course_list = []
        for course in courses:
            lector = self.db.query(User) \
                .filter(User.user_id == course.lector_id) \
                .first()

            seminarists = self.db.query(User) \
                .join(Group, User.user_id == Group.seminarist_id) \
                .filter(Group.course_id == course.course_id) \
                .all()

            seminarists_data = [{
                "seminarist_id": seminarist.user_id,
                "first_name": seminarist.first_name if seminarist else "",
                "last_name": seminarist.last_name if seminarist else ""
            } for seminarist in seminarists]

            course_data = {
                "course_id": course.course_id,
                "course_name": course.name,
                "description": course.description,
                "lector": {
                    "lector_id": course.lector_id,
                    "first_name": lector.first_name if lector else "",
                    "last_name": lector.last_name if lector else ""
                },
                "seminarists": seminarists_data if seminarists else None
            }
            course_list.append(course_data)

        return course_list, total

    def get_course_details(self, course_id: str, user_id: str, user_role: str) -> Optional[Dict]:
        if user_role == "teacher":
            return None

        if user_role == "admin":
            course = self.db.query(Course).filter(Course.course_id == course_id).first()
            if not course:
                return None

            lector = self.db.query(User).filter(User.user_id == course.lector_id).first()
            seminarists = self.db.query(User).join(Group, User.user_id == Group.seminarist_id) \
                .filter(Group.course_id == course_id) \
                .distinct() \
                .all()

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
                "seminarists": [
                    {
                        "seminarist_id": str(seminarist.user_id),
                        "first_name": seminarist.first_name,
                        "last_name": seminarist.last_name
                    } for seminarist in seminarists
                ],
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
                        "unit_id": str(unit.unit_id),
                        "name": unit.name,
                        "type": unit.type
                    } for unit in sorted_units]
                }
                course_data["blocks"].append(block_data)

            return course_data

        elif user_role == "student":
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

            lector = self.db.query(User).filter(User.user_id == course.lector_id).first()
            seminarist = self.db.query(User).join(Group, User.user_id == Group.seminarist_id) \
                .filter(Group.group_id == student.group_id) \
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
                "seminarist": {
                    "seminarist_id": str(seminarist.user_id) if seminarist else None,
                    "first_name": seminarist.first_name if seminarist else None,
                    "last_name": seminarist.last_name if seminarist else None
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
                        "unit_id": str(unit.unit_id),
                        "name": unit.name,
                        "type": unit.type
                    } for unit in sorted_units]
                }
                course_data["blocks"].append(block_data)

            return course_data
        return None

    def submit_sop(self, user_id: str, courses_data: List[Dict]) -> Dict:
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

            for course in courses_data:
                course_id = course["course_id"]
                blocks = course["blocks"]

                for block in blocks:
                    content = OrderedDict()
                    content["teacher_id"] = block.get("teacher_id")
                    content["questions_answers"] = []

                    for question in block["questions_answers"]:
                        q_data = {
                            "question": question["question"],
                            "type": question["question_type"]
                        }
                        if question["question_type"] == "rating":
                            q_data["answer"] = question["answer"]
                        else:
                            q_data["text_answer"] = question["text_answer"]

                        content["questions_answers"].append(q_data)

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
        if user_role != "teacher":
            return {
                "error": "Only teachers can view teacher SOP results",
                "status": 403
            }

        sop_blocks = self.db.query(SetBlock) \
            .filter(
            SetBlock.content.like(f'%"teacher_id": "{teacher_id}"%'),
            SetBlock.type.in_(["lecturer", "seminarist"])
        ) \
            .all()

        if not sop_blocks:
            return {
                "message": "No SOP results found for this teacher",
                "status": 404
            }

        course_results = {}
        text_comments = {}

        for block in sop_blocks:
            try:
                content = json.loads(block.content)
                qa_pairs = content.get("questions_answers", [])
                course_id = block.course_id

                if course_id not in course_results:
                    course_results[course_id] = {
                        "course_id": course_id,
                        "teaching_type": block.type,
                        "questions": {},
                        "text_comments": []
                    }

                for qa in qa_pairs:
                    question = qa["question"]
                    q_type = qa["type"]

                    if q_type == "rating":
                        answer = qa["answer"]
                        if question not in course_results[course_id]["questions"]:
                            course_results[course_id]["questions"][question] = {}

                        if answer not in course_results[course_id]["questions"][question]:
                            course_results[course_id]["questions"][question][answer] = 0

                        course_results[course_id]["questions"][question][answer] += 1
                    elif q_type == "text":
                        text_answer = qa["text_answer"]
                        course_results[course_id]["text_comments"].append({
                            "question": question,
                            "answer": text_answer
                        })

            except Exception as e:
                print(f"Error processing block {block.set_id}: {e}")
                continue

        formatted_results = []
        for course_id, course_data in course_results.items():
            questions_list = []

            for question, answers in course_data["questions"].items():
                answer_distribution = []
                for answer, count in sorted(answers.items()):
                    answer_distribution.append({
                        "answer": answer,
                        "count": count
                    })

                questions_list.append({
                    "question": question,
                    "answers": answer_distribution
                })

            formatted_results.append({
                "course_id": course_id,
                "teaching_type": course_data["teaching_type"],
                "questions": questions_list,
                "text_comments": course_data["text_comments"]
            })

        return {
            "data": formatted_results,
            "status": 200
        }

    def get_course_sop_results(self, course_id: str, current_user_id: str, current_user_role: str) -> Dict:
        if current_user_role not in ["teacher", "admin"]:
            return {
                "error": "Only course lecturers and admins can view course SOP results",
                "status": 403
            }

        if current_user_role == "teacher":
            course = self.db.query(Course) \
                .filter(
                Course.course_id == course_id,
                Course.lector_id == current_user_id
            ) \
                .first()
            if not course:
                return {
                    "error": "You can only view SOP for courses where you are the lecturer",
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
        course_text_comments = self._get_text_comments(course_id, "course")
        lector_text_comments = self._get_text_comments(course_id, "lecturer", course.lector_id)

        lector_data = {
            "lector_id": str(course.lector_id),
            "first_name": lector.first_name if lector else "",
            "last_name": lector.last_name if lector else "",
            "results": lector_results,
            "text_comments": lector_text_comments
        }

        seminarists = self.db.query(User) \
            .join(Group, User.user_id == Group.seminarist_id) \
            .filter(Group.course_id == course_id) \
            .all()

        seminarists_results = []
        for seminarist in seminarists:
            results = self._get_block_results(course_id, "seminarist", seminarist.user_id)
            text_comments = self._get_text_comments(course_id, "seminarist", seminarist.user_id)
            seminarists_results.append({
                "seminarist_id": str(seminarist.user_id),
                "first_name": seminarist.first_name,
                "last_name": seminarist.last_name,
                "results": results,
                "text_comments": text_comments
            })

        return {
            "data": {
                "course_results": course_block_results,
                "course_text_comments": course_text_comments,
                "lector": lector_data,
                "seminarists": seminarists_results
            },
            "status": 200
        }

    def _get_block_results(self, course_id: str, block_type: str, teacher_id: str = None) -> List[Dict]:
        query = self.db.query(SetBlock) \
            .filter(
            SetBlock.course_id == course_id,
            SetBlock.type == block_type
        )

        if teacher_id:
            query = query.filter(SetBlock.content.like(f'%"teacher_id": "{teacher_id}"%'))

        blocks = query.all()
        results = {}

        for block in blocks:
            try:
                content = json.loads(block.content)
                for qa in content.get("questions_answers", []):
                    if qa.get("type") == "rating":
                        question = qa["question"]
                        answer = qa["answer"]

                        if question not in results:
                            results[question] = {}
                        if answer not in results[question]:
                            results[question][answer] = 0
                        results[question][answer] += 1
            except:
                continue

        formatted_results = []
        for question, answers in results.items():
            answer_distribution = [{"answer": a, "count": c} for a, c in sorted(answers.items())]
            formatted_results.append({
                "question": question,
                "answers": answer_distribution
            })

        return formatted_results

    def _get_text_comments(self, course_id: str, block_type: str, teacher_id: str = None) -> List[Dict]:
        query = self.db.query(SetBlock) \
            .filter(
            SetBlock.course_id == course_id,
            SetBlock.type == block_type
        )

        if teacher_id:
            query = query.filter(SetBlock.content.like(f'%"teacher_id": "{teacher_id}"%'))

        blocks = query.all()
        text_comments = []

        for block in blocks:
            try:
                content = json.loads(block.content)
                for qa in content.get("questions_answers", []):
                    if qa.get("type") == "text":
                        text_comments.append({
                            "question": qa["question"],
                            "answer": qa["text_answer"]
                        })
            except:
                continue

        return text_comments

    def get_unit_by_id(self, unit_id: int, user_id: str) -> Optional[Dict]:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        unit = self.db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if not unit:
            return None

        if user.role == "admin":
            return self._format_unit_response(unit)

        if user.role == "teacher":
            is_lecturer = self.db.query(Course).filter(
                Course.course_id == unit.course_id,
                Course.lector_id == user_id
            ).first()

            is_seminarist = self.db.query(Group).filter(
                Group.course_id == unit.course_id,
                Group.seminarist_id == user_id
            ).first()

            if is_lecturer or is_seminarist:
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

        if test.deadline and datetime.now() > test.deadline:
            return {
                "error": f"The test deadline has expired {test.deadline.strftime('%Y-%m-%d %H:%M:%S')}",
                "status": 400
            }

        try:
            test_data = json.loads(test.questions)
            correct_answers = json.loads(test.answers)
        except (ValueError, TypeError):
            return {"error": "Invalid test data format", "status": 500}

        question_types = {str(item['id']): item['type'] for item in test_data}

        correct_answers_dict = {
            str(item['id']): set(item['answer'])
            for item in correct_answers
            if question_types.get(str(item['id'])) != 'custom'
        }

        results = []
        for user_answer in user_answers:
            question_id = str(user_answer['id'])
            question_type = question_types.get(question_id)

            if question_type == 'custom':
                user_response = user_answer.get('answer', [''])[0] if user_answer.get('answer') else ''
                results.append({
                    "id": int(question_id),
                    "is_right": user_response
                })
            else:
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
                results=json.dumps(results, ensure_ascii=False, indent=2)
            )
            self.db.add(test_result)
            self.db.commit()

            return results

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
                "data": {
                    "questions": formatted_questions,
                    "deadline": test.deadline
                },
                "status": 200
            }
        except (ValueError, TypeError):
            return {"error": "Invalid questions format", "status": 500}

    def get_student_test_results(self, test_id: str, student_id: str) -> Union[Dict, List]:
        test_result = self.db.query(TestResult).filter(
            TestResult.test_id == test_id,
            TestResult.user_id == student_id
        ).first()

        if not test_result:
            return []

        try:
            return json.loads(test_result.results)
        except (ValueError, TypeError):
            return {"error": "Invalid test results format", "status": 500}

    def check_user_exists(self, user_id: str) -> bool:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        return user is not None

    def update_test_results(self, test_id: str, user_id: str, results_data: List[Dict]) -> Dict:
        test_result = self.db.query(TestResult).filter(
            TestResult.test_id == test_id,
            TestResult.user_id == user_id
        ).first()

        if not test_result:
            return {"error": "Test results not found for this user", "status": 404}

        try:
            formatted_results = json.dumps(results_data, ensure_ascii=False, indent=2)
            test_result.results = formatted_results
            self.db.commit()
            return {
                "message": "Test results updated successfully",
                "status": 200
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error updating test results: {e}")
            return {
                "error": "Failed to update test results",
                "status": 500
            }

    def generate_test_id(self) -> str:
        existing_ids = [r[0] for r in self.db.query(Test.test_id).all()]
        numbers = []

        for test_id in existing_ids:
            if test_id.startswith('test'):
                try:
                    numbers.append(int(test_id[4:]))
                except ValueError:
                    continue

        if numbers:
            max_num = max(numbers)
            all_numbers = set(range(1, max_num + 1))
            existing_numbers = set(numbers)
            missing_numbers = all_numbers - existing_numbers
            if missing_numbers:
                return f"test{min(missing_numbers)}"
            return f"test{max_num + 1}"
        return "test1"

    def create_test(self, test_id: str, questions: List[Dict], answers: List[Dict],
                    deadline: Optional[datetime] = None) -> Dict:
        try:
            def order_question_fields(q):
                return {
                    "id": q["id"],
                    "text": q["text"],
                    "type": q["type"],
                    "answers": q.get("answers", [])
                }

            def order_answer_fields(a):
                return {
                    "id": a["id"],
                    "answer": a["answer"]
                }

            ordered_questions = [order_question_fields(q) for q in questions]
            ordered_answers = [order_answer_fields(a) for a in answers]

            questions_json = json.dumps(
                ordered_questions,
                ensure_ascii=False,
                indent=None,
                separators=(',', ':'),
                sort_keys=False
            )

            answers_json = json.dumps(
                ordered_answers,
                ensure_ascii=False,
                indent=None,
                separators=(',', ':'),
                sort_keys=False
            )

            new_test = Test(
                test_id=test_id,
                questions=questions_json,
                answers=answers_json,
                deadline=deadline
            )

            self.db.add(new_test)
            self.db.commit()

            return {
                "test_id": test_id,
                "message": "Test created successfully",
                "status": 201
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error creating test: {e}")
            return {
                "error": "Failed to create test",
                "status": 500
            }

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def generate_course_id(self) -> str:
        existing_ids = [course.course_id for course in self.db.query(Course.course_id).all()]

        max_num = 0
        for course_id in existing_ids:
            if course_id.startswith('COURSE'):
                try:
                    num = int(course_id[6:])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue

        return f"COURSE{max_num + 1:03d}"

    def create_course(self, course_id: str, name: str, description: str, lector_id: str, groups: List[Dict]) -> Dict:
        try:
            new_course = Course(
                course_id=course_id,
                name=name,
                description=description,
                lector_id=lector_id
            )
            self.db.add(new_course)

            for group in groups:
                new_group = Group(
                    group_id=group['group_id'],
                    course_id=course_id,
                    seminarist_id=group['seminarist_id']
                )
                self.db.add(new_group)

            self.db.commit()

            return {
                "course_id": course_id,
                "status": 201
            }

        except Exception as e:
            self.db.rollback()
            print(f"Error creating course: {e}")
            return {
                "error": "Database error while creating course",
                "status": 500
            }

    def update_course(self, course_id: str, user_role: str, update_data: Dict) -> Dict:
        course = self.db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            return {"error": "Course not found", "status": 404}

        try:
            if 'name' in update_data:
                course.name = update_data['name']
            if 'description' in update_data:
                course.description = update_data['description']

            if 'lector_id' in update_data and user_role == "admin":
                course.lector_id = update_data['lector_id']

            if 'groups' in update_data:
                self.db.query(Group).filter(Group.course_id == course_id).delete()
                for group in update_data['groups']:
                    new_group = Group(
                        group_id=group['group_id'],
                        course_id=course_id,
                        seminarist_id=group['seminarist_id']
                    )
                    self.db.add(new_group)

            self.db.commit()

            return {
                "message": "Course has been successfully updated.",
                "status": 200
            }

        except Exception as e:
            self.db.rollback()
            print(f"Error updating course: {e}")
            return {"error": "Database error while updating course", "status": 500}

    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        return self.db.query(Course).filter(Course.course_id == course_id).first()

    def generate_block_id(self, course_id: str) -> str:
        existing_blocks = self.db.query(Block.block_id) \
            .filter(Block.course_id == course_id) \
            .all()

        max_num = 0
        for block_id, in existing_blocks:
            if block_id.startswith('block') and '_' in block_id:
                try:
                    num_part = block_id.split('_')[0][5:]
                    num = int(num_part)
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue

        return f"block{max_num + 1}_{course_id.lower()}"

    def create_block(self, block_id: str, course_id: str, name: str) -> Dict:
        try:
            new_block = Block(
                block_id=block_id,
                course_id=course_id,
                name=name
            )
            self.db.add(new_block)
            self.db.commit()

            return {
                "block_id": block_id,
                "status": 201
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error creating block: {e}")
            return {
                "error": "Database error while creating block",
                "status": 500
            }

    def get_block(self, block_id: str) -> Dict:
        block = self.db.query(Block).filter(Block.block_id == block_id).first()
        if not block:
            return {"error": "Block not found", "status": 404}

        units = self.db.query(Unit).filter(
            Unit.block_id == block_id,
            Unit.course_id == block.course_id
        ).all()

        units_data = []
        for unit in units:
            units_data.append(unit.unit_id)

        return {
            "block_id": block.block_id,
            "course_id": block.course_id,
            "name": block.name,
            "units": units_data,
            "status": 200
        }

    def is_student_in_course(self, course_id: str, student_id: str) -> bool:
        student = self.db.query(User).filter(
            User.user_id == student_id,
            User.role == 'student'
        ).first()

        if not student or not student.group_id:
            return False

        return self.db.query(Group).filter(
            Group.group_id == student.group_id,
            Group.course_id == course_id
        ).first() is not None

    def get_query_block(self, block_id: str):
        return self.db.query(Block).filter(Block.block_id == block_id).first()

    def update_block(self, block_id: str, name: str) -> Dict:
        block = self.db.query(Block).filter(Block.block_id == block_id).first()
        if not block:
            return {"error": "Block not found", "status": 404}

        try:
            block.name = name
            self.db.commit()

            return {
                "message": "Block has been updated successfully",
                "status": 200
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error updating block: {e}")
            return {
                "error": "Database error while updating block",
                "status": 500
            }

    def create_unit(self, block_id: str, course_id: str, name: str, unit_type: str, content: Union[str, dict]) -> Dict:
        try:
            max_id = self.db.query(func.max(Unit.unit_id)).scalar() or 0
            new_unit_id = max_id + 1

            if unit_type == "test":
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        raise ValueError("For test units, content must be a valid JSON string with 'test_id'")
                formatted_content = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
            else:
                formatted_content = str(content) if not isinstance(content, str) else content

            new_unit = Unit(
                unit_id=new_unit_id,
                block_id=block_id,
                course_id=course_id,
                name=name,
                type=unit_type,
                content=formatted_content
            )
            self.db.add(new_unit)
            self.db.commit()

            return {
                "unit_id": new_unit_id,
                "status": 201
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error creating unit: {e}")
            return {
                "error": str(e),
                "status": 500
            }

    def update_unit(self, unit_id: int, update_data: Dict) -> Dict:
        unit = self.db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if not unit:
            return {"error": "Unit not found", "status": 404}

        try:
            if 'name' in update_data:
                unit.name = update_data['name']

            if 'type' in update_data:
                unit.type = update_data['type']

            if 'content' in update_data:
                if unit.type == "test" and isinstance(update_data['content'], dict):
                    unit.content = json.dumps(update_data['content'], ensure_ascii=False)
                else:
                    unit.content = str(update_data['content'])

            self.db.commit()

            return {
                "message": "Unit updated successfully",
                "status": 200
            }
        except Exception as e:
            self.db.rollback()
            print(f"Error updating unit: {e}")
            return {
                "error": "Database error while updating unit",
                "status": 500
            }

    def get_course_students(
            self,
            course_id: str,
            user_id: str,
            user_role: str,
            limit: int = 20,
            offset: int = 0,
            search: str = ''
    ) -> Dict:
        try:
            if limit == 0:
                return {
                    "students": [],
                    "total": 0,
                    "status": 200
                }

            if user_role == "admin":
                query = (self.db.query(User)
                         .join(Group, User.group_id == Group.group_id)
                         .filter(Group.course_id == course_id,
                                 User.role == "student"))

            elif user_role == "teacher":
                if not self.is_course_lector_or_seminarist(course_id, user_id):
                    return {"error": "Access denied - not your course", "status": 403}

                if self.is_course_lector(course_id, user_id):
                    query = (self.db.query(User)
                             .join(Group, User.group_id == Group.group_id)
                             .filter(Group.course_id == course_id,
                                     User.role == "student"))
                else:
                    teacher_groups = select(Group.group_id).where(
                        Group.course_id == course_id,
                        Group.seminarist_id == user_id
                    )
                    query = (self.db.query(User)
                             .filter(User.role == "student",
                                     User.group_id.in_(teacher_groups)))
            else:
                return {"error": "Access denied", "status": 403}

            if search.strip():
                query = query.filter(
                    or_(
                        User.first_name.ilike(f"%{search}%"),
                        User.last_name.ilike(f"%{search}%"),
                        User.email.ilike(f"%{search}%")
                    )
                )

            total = query.count()
            students = query.order_by(User.last_name, User.first_name).offset(offset).limit(limit).all()

            students_data = [{
                "student_id": s.user_id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "email": s.email,
                "group_id": s.group_id
            } for s in students]

            return {
                "students": students_data,
                "total": total,
                "status": 200
            }

        except Exception as e:
            print(f"Error in get_course_students: {str(e)}")
            return {"error": "Internal server error", "status": 500}
