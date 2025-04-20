from flask import Flask, request, make_response, jsonify, Response
from functools import wraps
from pydantic import ValidationError
from course.service import CourseService
from validation.course_schemas import (
    CourseCreateRequest,
    CourseUpdateRequest,
    PaginatedResponse,
    SOPSubmitRequest,
    TeacherSOPResultsRequest,
    CourseSOPResultsRequest,
    TestSubmitRequest,
    TestResultsResponse,
    TestDetailsResponse,
    StudentTestResultsRequest,
    TestUpdateRequest,
    TestCreateRequest,
    BlockCreateRequest,
    BlockUpdateRequest,
    BlockResponse,
    UnitCreateRequest,
    UnitUpdateRequest,
    UnitResponse,
    CourseStudentsRequest,
    PaginatedResponse,
    AnswerItem
)
from datetime import datetime
from validation.auth_schemas import TokenPayload
from collections import OrderedDict
import json
import jwt
import os

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

JWT_ALGORITHM = "RS256"
PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_FILE', '/app/configs/signature.pub')

with open(PUBLIC_KEY_PATH, 'rb') as key_file:
    public_key = key_file.read()


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return make_response("Missing or invalid Authorization header", 401)

        token = auth_header.split(' ')[1]
        try:
            payload = decode_jwt(token)
            request.user = TokenPayload(**payload)
        except ValidationError as e:
            return make_response(jsonify({"error": str(e)}), 401)
        except jwt.ExpiredSignatureError:
            return make_response("Token expired", 401)
        except jwt.InvalidTokenError:
            return make_response("Invalid token", 401)
        return f(*args, **kwargs)

    return decorated


@app.route("/courses", methods=["GET", "POST"])
@token_required
def handle_courses():
    if request.method == "POST":
        try:
            if request.user.role != "admin":
                return make_response("Only admin can create courses", 403)

            course_data = CourseCreateRequest(**request.get_json())
            service = CourseService()
            result = service.create_course(**course_data.dict())

            if 'error' in result:
                return make_response(
                    json.dumps(result, indent=2, ensure_ascii=False),
                    result['status'],
                    {'Content-Type': 'application/json; charset=utf-8'}
                )

            return make_response(
                json.dumps(result, indent=2, ensure_ascii=False),
                201,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        except ValidationError as e:
            return make_response(
                json.dumps({"error": str(e)}, indent=2, ensure_ascii=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )
        except Exception as e:
            print(f"Error creating course: {e}")
            return make_response("Internal server error", 500)

    try:
        service = CourseService()
        user_role = request.user.role

        if user_role == "teacher":
            return make_response(
                json.dumps({"error": "This endpoint is only for students and admins"},
                           indent=2, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        limit = max(1, min(100, request.args.get('limit', default=20, type=int)))
        offset = max(0, request.args.get('offset', default=0, type=int))
        search = request.args.get('search', default='', type=str)
        student_id = request.args.get('student_id', type=str)

        if student_id and user_role != "admin":
            return make_response(
                json.dumps({"error": "Only admin can specify student_id parameter"},
                           indent=2, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        if user_role == "admin" and student_id:
            if not service.validate_student_id(student_id):
                return make_response(
                    json.dumps({"error": "Invalid student_id"},
                               indent=2, ensure_ascii=False),
                    400,
                    {'Content-Type': 'application/json; charset=utf-8'}
                )
            target_user_id = student_id
        else:
            target_user_id = request.user.user_id

        if user_role == "admin" and not student_id:
            courses_info, total = service.get_all_courses_info(
                search=search,
                limit=limit,
                offset=offset
            )
        else:
            courses_info, total = service.get_student_courses_info(
                user_id=target_user_id,
                search=search,
                limit=limit,
                offset=offset
            )

        response_data = PaginatedResponse(
            data=courses_info,
            total=total,
            limit=limit,
            offset=offset
        )

        return make_response(
            json.dumps(response_data.dict(), indent=2, ensure_ascii=False),
            200,
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except Exception as e:
        print(f"Error: {e}")
        return make_response(
            json.dumps({"error": "Internal server error"}, indent=2, ensure_ascii=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/courses/<course_id>", methods=["GET", "PUT"])
@token_required
def handle_course_details(course_id):
    try:
        user_role = request.user.role
        user_id = request.user.user_id
        service = CourseService()

        if request.method == "PUT":
            if user_role not in ["admin", "teacher"]:
                return Response("Course not found or access denied", status=404)

            if user_role == "teacher":
                course = service.queries.get_course(course_id)
                if not course or course.lector_id != user_id:
                    return Response("Course not found or access denied", status=404)

            try:
                update_data = CourseUpdateRequest(**request.get_json()).dict(exclude_unset=True)
            except ValidationError as e:
                return make_response(jsonify({"error": str(e)}), 400)

            result = service.update_course(
                course_id=course_id,
                user_role=user_role,
                user_id=user_id,
                update_data=update_data
            )

            if 'error' in result:
                return make_response(jsonify(result), result['status'])
            return make_response(jsonify(result), 200)

        else:
            course_data = service.get_course_details(course_id, request.user.user_id)
            if not course_data:
                return Response("Course not found or access denied", status=404)

            if user_role == "student":
                response_data = OrderedDict([
                    ("success", True),
                    ("data", OrderedDict([
                        ("name", course_data["name"]),
                        ("description", course_data["description"]),
                        ("lector", OrderedDict([
                            ("lector_id", course_data["lector"]["lector_id"]),
                            ("first_name", course_data["lector"]["first_name"]),
                            ("last_name", course_data["lector"]["last_name"])
                        ])),
                        ("seminarist", OrderedDict([
                            ("seminarist_id", course_data["seminarist"]["seminarist_id"]),
                            ("first_name", course_data["seminarist"]["first_name"]),
                            ("last_name", course_data["seminarist"]["last_name"])
                        ])),
                        ("blocks", course_data["blocks"])
                    ]))
                ])
            else:  # admin
                response_data = OrderedDict([
                    ("success", True),
                    ("data", OrderedDict([
                        ("name", course_data["name"]),
                        ("description", course_data["description"]),
                        ("lector", OrderedDict([
                            ("lector_id", course_data["lector"]["lector_id"]),
                            ("first_name", course_data["lector"]["first_name"]),
                            ("last_name", course_data["lector"]["last_name"])
                        ])),
                        ("seminarists", [
                            OrderedDict([
                                ("seminarist_id", s["seminarist_id"]),
                                ("first_name", s["first_name"]),
                                ("last_name", s["last_name"])
                            ]) for s in course_data["seminarists"]
                        ]),
                        ("blocks", course_data["blocks"])
                    ]))
                ])

            return Response(
                json.dumps(response_data, ensure_ascii=False, indent=2),
                status=200,
                content_type='application/json'
            )

    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/sop", methods=["POST"])
@token_required
def submit_sop():
    try:
        raw_data = request.get_json()
        if isinstance(raw_data, list):
            validated_data = SOPSubmitRequest(courses=raw_data)
        else:
            validated_data = SOPSubmitRequest(**raw_data)

        service = CourseService()
        result = service.submit_sop(
            user_id=request.user.user_id,
            sop_data=validated_data.dict()
        )

        return jsonify(result), result.get("status", 200)

    except ValidationError as e:
        return make_response(jsonify({"error": str(e)}), 400)
    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/sop/teacher_results", methods=["GET"])
@token_required
def get_teacher_sop_results():
    try:
        service = CourseService()
        user_id = request.user.user_id
        user_role = request.user.role
        teacher_id = request.args.get('teacher_id', type=str)

        if user_role == "student":
            return make_response(
                json.dumps({"error": "Access denied", "status": 403}, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        if user_role == "admin" and teacher_id:
            target_teacher_id = teacher_id
            target_role = service.determine_teacher_role(teacher_id)
        elif user_role == "admin" and not teacher_id:
            return make_response(
                json.dumps({"error": "Please specify teacher_id parameter", "status": 403}, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )
        else:
            target_teacher_id = user_id
            target_role = user_role

        if target_role != "teacher":
            return make_response(
                json.dumps({"error": "teacher_id is incorrect - either doesn't exist or not a teacher", "status": 403},
                           ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        if teacher_id and user_role != "admin":
            return make_response(
                json.dumps({"error": "Only admin can specify teacher_id parameter", "status": 403}, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.get_teacher_sop_results(target_teacher_id, target_role)

        response = make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 200)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        return make_response(
            json.dumps({"error": "Internal server error", "status": 500}, ensure_ascii=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/sop/course_results/<course_id>", methods=["GET"])
@token_required
def get_course_sop_results(course_id):
    try:
        service = CourseService()
        user_id = request.user.user_id
        user_role = request.user.role

        result = service.get_course_sop_results(course_id, user_id, user_role)

        response = make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 200)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        error_response = {
            "error": "Internal server error",
            "status": 500
        }
        return make_response(
            json.dumps(error_response, ensure_ascii=False, indent=2),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/tests", methods=["POST"])
@token_required
def create_test():
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")

        if user_role not in ["teacher"]:
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        try:
            test_data = TestCreateRequest(**request.get_json())
        except ValidationError as e:
            return jsonify({"error": str(e), "status": 400}), 400

        data = test_data.dict()
        result = service.create_test(
            questions=data["questions"],
            answers=data["answers"],
            deadline=data.get("deadline")
        )

        return make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 201),
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except Exception as e:
        print(f"Error: {e}")
        response_data = {
            "error": "Internal server error",
            "status": 500
        }
        return make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/test_results/<test_id>", methods=["POST"])
@token_required
def submit_test_results(test_id):
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")

        if not user_id:
            return make_response("User ID not found in token", 400)

        access_error = service.verify_test_access(user_id, user_role, test_id)
        if access_error:
            return jsonify(access_error), access_error["status"]

        raw_data = request.get_json()
        test_data = TestSubmitRequest(answers=raw_data)

        result = service.submit_test_results(
            user_id=user_id,
            test_id=test_id,
            user_answers=test_data.answers
        )

        if isinstance(result, dict) and "error" in result:
            return jsonify(result), result.get("status", 400)

        response = TestResultsResponse(
            test_id=test_id,
            results=result,
            submitted_at=datetime.now()
        )
        return jsonify(response.dict()), 201

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/tests/<test_id>", methods=["GET"])
@token_required
def get_test_or_results(test_id):
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")

        if not user_id:
            return json_response({"success": False, "error": "User ID not found"}, 400)

        access_error = service.verify_test_access(user_id, user_role, test_id)
        if access_error:
            return json_response({
                "success": False,
                "error": access_error.get("error"),
                "status": access_error.get("status", 403)
            }, access_error.get("status", 403))

        raw_data = service.get_test_or_results(user_id, test_id)

        if "error" in raw_data:
            return json_response({
                "success": False,
                "error": raw_data["error"],
                "status": raw_data["status"]
            }, raw_data["status"])

        if "data" in raw_data:
            try:
                prepared_data = {
                    "deadline": raw_data["data"].get("deadline"),
                    "questions": [
                        {
                            "id": q.get("id"),
                            "text": q.get("text"),
                            "type": q.get("type"),
                            "answers": q.get("answers", [])
                        }
                        for q in raw_data["data"]["questions"]
                    ]
                }

                validated = TestDetailsResponse(**prepared_data)
                response_data = {
                    "success": True,
                    "deadline": validated.deadline.strftime(
                        '%a, %d %b %Y %H:%M:%S GMT') if validated.deadline else None,
                    "questions": [q.dict() for q in validated.questions]
                }

                return json_response(response_data, 200)

            except Exception as e:
                return json_response({
                    "success": False,
                    "error": f"Data validation failed: {str(e)}"
                }, 400)

        else:
            return json_response({
                "success": True,
                "results": raw_data["results"]
            }, 200)

    except Exception as e:
        print(f"Server error: {str(e)}")
        return json_response({
            "success": False,
            "error": "Internal server error"
        }, 500)


def json_response(data: dict, status_code: int):
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False),
        status=status_code,
        content_type='application/json; charset=utf-8'
    )


@app.route("/test_results/<test_id>/user/<user_id>", methods=["GET"])
@token_required
def get_student_test_results(test_id, user_id):
    try:
        service = CourseService()
        teacher_id = request.user.get("user_id")
        teacher_role = request.user.get("role")

        request_data = StudentTestResultsRequest(
            teacher_id=teacher_id,
            teacher_role=teacher_role,
            test_id=test_id,
            student_id=user_id
        )

        user_exists = service.check_user_exists(request_data.student_id)
        if not user_exists:
            response_data = {"error": "User not found", "status": 404}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                404,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.get_student_test_results(
            teacher_id=request_data.teacher_id,
            teacher_role=request_data.teacher_role,
            test_id=request_data.test_id,
            student_id=request_data.student_id
        )

        if isinstance(result, dict) and "error" in result:
            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
                result.get("status", 400),
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        response_data = result if result is not None else {}
        if not isinstance(response_data, (dict, list)):
            response_data = {"results": response_data}

        response = TestResultsResponse(
            data=response_data,
            status=200
        )

        return make_response(
            json.dumps(response.dict(), ensure_ascii=False, indent=2, sort_keys=False),
            200,
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except ValidationError as e:
        response_data = {
            "error": str(e),
            "status": 400
        }
        return make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            400,
            {'Content-Type': 'application/json; charset=utf-8'}
        )
    except Exception as e:
        print(f"Error: {e}")
        response_data = {
            "error": "Internal server error",
            "status": 500
        }
        return make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/test_results/<test_id>/user/<user_id>", methods=["POST"])
@token_required
def update_student_test_results(test_id, user_id):
    try:
        service = CourseService()
        teacher_id = request.user.get("user_id")
        teacher_role = request.user.get("role")

        if teacher_role != "teacher":
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        raw_data = request.get_json()
        if not raw_data or not isinstance(raw_data, list):
            response_data = {"error": "Request data must be a list", "status": 400}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        try:
            validated_data = [AnswerItem(**item) for item in raw_data]
        except Exception as e:
            response_data = {"error": f"Validation error: {str(e)}", "status": 400}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.update_student_test_results(
            teacher_id=teacher_id,
            teacher_role=teacher_role,
            test_id=test_id,
            student_id=user_id,
            results_data=[item.dict() for item in validated_data]
        )

        return make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 200),
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except Exception as e:
        print(f"Error: {e}")
        response_data = {
            "error": "Internal server error",
            "status": 500
        }
        return make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/courses/<course_id>/blocks", methods=["POST"])
@token_required
def create_block(course_id):
    try:
        user_role = request.user.get("role")

        if user_role == "admin" or user_role == "student":
            return jsonify({"error": "Access denied", "status": 403}), 403

        if user_role == "teacher":
            service = CourseService()
            if not service.is_course_lector_or_seminarist(course_id, request.user.get("user_id")):
                return jsonify({"error": "Access denied", "status": 403}), 403

        block_data = BlockCreateRequest(**request.get_json())

        result = service.create_block(
            course_id=course_id,
            name=block_data.name,
            user_id=request.user.get("user_id"),
            user_role=user_role
        )

        if 'error' in result:
            return jsonify(result), result['status']

        return jsonify(result), 201

    except ValidationError as e:
        return jsonify({"error": str(e), "status": 400}), 400
    except Exception as e:
        print(f"Error creating block: {e}")
        return jsonify({"error": "Internal server error", "status": 500}), 500


@app.route("/blocks/<block_id>", methods=["GET", "PUT"])
@token_required
def handle_block(block_id):
    try:
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")
        service = CourseService()

        if request.method == "GET":
            if user_role == "student":
                if not service.is_student_in_block_course(block_id, user_id):
                    return jsonify({"error": "Access denied", "status": 403}), 403
            elif user_role == "teacher":
                if not service.is_block_lector_or_seminarist(block_id, user_id):
                    return jsonify({"error": "Access denied", "status": 403}), 403

            result = service.get_block(
                block_id=block_id,
                user_id=user_id,
                user_role=user_role
            )

            if 'error' in result:
                return jsonify(result), result['status']

            response = BlockResponse(
                name=result["name"],
                units=result["units"]
            )
            return Response(
                json.dumps(response.dict(), ensure_ascii=False),
                mimetype='application/json; charset=utf-8'
            )

        else:  # PUT
            if user_role != "teacher":
                return jsonify({"error": "Access denied", "status": 403}), 403

            if not service.is_block_lector_or_seminarist(block_id, user_id):
                return jsonify({"error": "Access denied", "status": 403}), 403

            update_data = BlockUpdateRequest(**request.get_json())

            result = service.update_block(
                block_id=block_id,
                name=update_data.name,
                user_id=user_id,
                user_role=user_role
            )

            return jsonify(result), result.get("status", 200)

    except ValidationError as e:
        return jsonify({"error": str(e), "status": 400}), 400
    except Exception as e:
        print(f"Error handling block: {e}")
        return jsonify({"error": "Internal server error", "status": 500}), 500


@app.route("/blocks/<block_id>/units", methods=["POST"])
@token_required
def create_unit(block_id):
    try:
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")
        service = CourseService()

        if user_role == "student" or user_role == "admin":
            return make_response(
                json.dumps({"error": "Access denied", "status": 403}, ensure_ascii=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        if user_role == "teacher":
            if not service.is_block_lector_or_seminarist(block_id, user_id):
                return make_response(
                    json.dumps({"error": "Access denied", "status": 403}, ensure_ascii=False),
                    403,
                    {'Content-Type': 'application/json; charset=utf-8'}
                )

        unit_data = UnitCreateRequest(**request.get_json())

        result = service.create_unit(
            block_id=block_id,
            name=unit_data.name,
            unit_type=unit_data.type,
            content=unit_data.content,
            user_id=user_id,
            user_role=user_role
        )

        if 'error' in result:
            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2),
                result['status'],
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        return make_response(
            json.dumps(result, ensure_ascii=False, indent=2),
            201,
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except ValidationError as e:
        return make_response(
            json.dumps({"error": str(e), "status": 400}, ensure_ascii=False),
            400,
            {'Content-Type': 'application/json; charset=utf-8'}
        )
    except Exception as e:
        print(f"Error creating unit: {e}")
        return make_response(
            json.dumps({"error": "Internal server error", "status": 500}, ensure_ascii=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/units/<int:unit_id>", methods=["GET", "PUT"])
@token_required
def handle_unit(unit_id):
    try:
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")
        service = CourseService()

        if request.method == "GET":
            if not user_id:
                return make_response(
                    json.dumps({"error": "User ID not found in token", "status": 400}, ensure_ascii=False),
                    400,
                    {'Content-Type': 'application/json; charset=utf-8'}
                )
            if user_role == "student":
                if not service.is_unit_accessible_to_student(unit_id, user_id):
                    return jsonify({"error": "Access denied", "status": 403}), 403
            elif user_role == "teacher":
                if not service.is_unit_lector_or_seminarist(unit_id, user_id):
                    return jsonify({"error": "Access denied", "status": 403}), 403

            unit_data = service.get_unit_by_id(unit_id, user_id)
            if not unit_data:
                return make_response(
                    json.dumps({"error": "Unit not found or access denied", "status": 404}, ensure_ascii=False),
                    404,
                    {'Content-Type': 'application/json; charset=utf-8'}
                )

            content = unit_data["content"]
            if unit_data["type"] == "test" and isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass

            response = UnitResponse(
                name=unit_data["name"],
                type=unit_data["type"],
                content=content
            )

            return make_response(
                json.dumps(response.dict(), ensure_ascii=False, indent=2, sort_keys=False),
                200,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        else:  # PUT
            if user_role == "student" or user_role == "admin":
                return make_response(
                    json.dumps({"error": "Access denied", "status": 403}, ensure_ascii=False),
                    403,
                    {'Content-Type': 'application/json; charset=utf-8'}
                )

            else:
                if not service.is_unit_lector_or_seminarist(unit_id, user_id):
                    return make_response(
                        json.dumps({"error": "Access denied", "status": 403}, ensure_ascii=False),
                        403,
                        {'Content-Type': 'application/json; charset=utf-8'}
                    )

            update_data = UnitUpdateRequest(**request.get_json())

            result = service.update_unit(
                unit_id=unit_id,
                update_data=update_data.dict(exclude_unset=True),
                user_id=user_id,
                user_role=user_role
            )

            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2),
                result.get("status", 200),
                {'Content-Type': 'application/json; charset=utf-8'}
            )

    except ValidationError as e:
        return make_response(
            json.dumps({"error": str(e), "status": 400}, ensure_ascii=False),
            400,
            {'Content-Type': 'application/json; charset=utf-8'}
        )
    except Exception as e:
        print(f"Error handling unit: {e}")
        return make_response(
            json.dumps({"error": "Internal server error", "status": 500}, ensure_ascii=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


@app.route("/courses/<course_id>/students", methods=["GET"])
@token_required
def get_course_students(course_id):
    try:
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)

        if limit == 0:
            return make_response(
                json.dumps({
                    "data": [],
                    "total": 0,
                    "limit": 0,
                    "offset": offset
                }, ensure_ascii=False),
                200,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        query_params = CourseStudentsRequest(
            course_id=course_id,
            user_id=request.user.get("user_id"),
            user_role=request.user.get("role"),
            limit=max(1, min(100, request.args.get('limit', default=20, type=int))),
            offset=max(0, request.args.get('offset', default=0, type=int)),
            search=request.args.get('search', default='', type=str)
        )

        service = CourseService()
        result = service.get_course_students(**query_params.dict())

        if 'error' in result:
            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2),
                result['status'],
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        response = PaginatedResponse(
            data=result["students"],
            total=result["total"],
            limit=query_params.limit,
            offset=query_params.offset
        )

        return make_response(
            json.dumps(response.dict(), ensure_ascii=False, indent=2, sort_keys=False),
            200,
            {'Content-Type': 'application/json; charset=utf-8'}
        )

    except ValidationError as e:
        return make_response(
            json.dumps({"error": str(e), "status": 400}, ensure_ascii=False),
            400,
            {'Content-Type': 'application/json; charset=utf-8'}
        )
    except Exception as e:
        print(f"Error getting course students: {e}")
        return make_response(
            json.dumps({"error": "Internal server error", "status": 500}, ensure_ascii=False),
            500,
            {'Content-Type': 'application/json; charset=utf-8'}
        )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
