from flask import Flask, request, make_response, jsonify, json
from flask import Response
import jwt
import os
from functools import wraps
from course.service import CourseService
from collections import OrderedDict

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
            request.user = payload
        except jwt.ExpiredSignatureError:
            return make_response("Token expired", 401)
        except jwt.InvalidTokenError:
            return make_response("Invalid token", 401)
        return f(*args, **kwargs)

    return decorated


@app.route("/courses", methods=["GET"])
@token_required
def get_student_courses():
    try:
        service = CourseService()
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)
        search = request.args.get('search', default='', type=str)
        student_id = request.args.get('student_id', type=str)
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")

        if not user_id:
            return make_response("User ID not found in token", 400)

        if user_role in ["lecturer", "seminarist"]:
            return make_response(
                "This endpoint is only for students and admins",
                403
            )

        if user_role == "admin" and student_id:
            is_valid_student = service.validate_student_id(student_id)
            if not is_valid_student:
                return make_response(
                    "student_id is incorrect - either doesn't exist or not a student",
                    400
                )
            target_user_id = student_id
        else:
            target_user_id = user_id

        if student_id and user_role != "admin":
            return make_response("Only admin can specify student_id parameter", 403)

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

        response = make_response(
            json.dumps({
                "success": True,
                "data": courses_info,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }, ensure_ascii=False, indent=2),
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/courses/<course_id>", methods=["GET"])
@token_required
def get_course_details(course_id):
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        if not user_id:
            return Response("User ID not found in token", status=400)

        course_data = service.get_course_details(course_id, user_id)
        if not course_data:
            return Response("Course not found or access denied", status=404)

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
                ("blocks", course_data["blocks"])
            ]))
        ])

        json_response = json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False)
        return Response(json_response, status=200, content_type='application/json')

    except Exception as e:
        print(f"Error: {e}")
        return Response("Internal server error", status=500)


@app.route("/sop", methods=["POST"])
@token_required
def submit_sop():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return make_response("Invalid request format", 400)

        service = CourseService()
        result = service.submit_sop(
            user_id=request.user["user_id"],
            sop_data=data
        )

        return jsonify(result), result.get("status", 500)
    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/sop/teacher_results", methods=["GET"])
@token_required
def get_teacher_sop_results():
    try:
        service = CourseService()
        user_id = request.user["user_id"]
        user_role = request.user.get("role")
        teacher_id = request.args.get('teacher_id', type=str)
        if user_role == "student":
            return make_response("Access denied", 403)

        if user_role == "admin" and teacher_id:
            target_teacher_id = teacher_id
            target_role = service.determine_teacher_role(teacher_id)
        elif user_role == "admin" and not teacher_id:
            return make_response("Please specify teacher_id parameter", 403)
        else:
            target_teacher_id = user_id
            target_role = user_role

        if target_role not in ["lecturer", "seminarist"]:
            return make_response("teacher_id is incorrect - either doesn't exist or not a teacher", 403)

        if teacher_id and user_role != "admin":
            return make_response("Only admin can specify teacher_id parameter", 403)

        result = service.get_teacher_sop_results(target_teacher_id, target_role)

        response = make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 200)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/sop/course_results/<course_id>", methods=["GET"])
@token_required
def get_course_sop_results(course_id):
    try:
        service = CourseService()
        user_id = request.user["user_id"]
        user_role = request.user.get("role")
        result = service.get_course_sop_results(course_id, user_id, user_role)

        response = make_response(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
            result.get("status", 200)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/units/<int:unit_id>", methods=["GET"])
@token_required
def get_unit(unit_id):
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        if not user_id:
            return make_response("User ID not found in token", 400)

        unit_data = service.get_unit_by_id(unit_id, user_id)
        if not unit_data:
            return make_response("Unit not found or access denied", 404)

        try:
            content = json.loads(unit_data["content"])
        except (ValueError, TypeError):
            content = unit_data["content"]

        response_data = {
            "success": True,
            "data": {
                "name": unit_data["name"],
                "type": unit_data["type"],
                "content": content
            }
        }

        response = make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            200
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


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

        data = request.get_json()
        if not data or not isinstance(data, list):
            return make_response("Invalid request format", 400)

        result = service.submit_test_results(user_id, test_id, data)

        if isinstance(result, dict) and "error" in result:
            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2),
                result.get("status", 400),
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        return make_response(
            json.dumps({"data": result, "status": 201}, ensure_ascii=False, indent=2),
            201,
            {'Content-Type': 'application/json; charset=utf-8'}
        )

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
            response_data = OrderedDict([
                ("success", False),
                ("error", "User ID not found in token")
            ])
            json_response = json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False)
            return Response(json_response, status=400, content_type='application/json')

        access_error = service.verify_test_access(user_id, user_role, test_id)
        if access_error:
            response_data = OrderedDict([
                ("success", False),
                ("error", access_error.get("error")),
                ("status", access_error.get("status"))
            ])
            json_response = json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False)
            return Response(json_response, status=access_error.get("status", 403),
                            content_type='application/json')

        result = service.get_test_or_results(user_id, test_id)

        if "error" in result:
            response_data = OrderedDict([
                ("success", False),
                ("error", result["error"]),
                ("status", result["status"])
            ])
            status_code = result["status"]
        else:
            if "data" in result:
                response_data = OrderedDict([
                    ("success", True),
                    ("data", result["data"])
                ])
            else:
                response_data = OrderedDict([
                    ("success", True),
                    ("results", result["results"])
                ])
            status_code = result.get("status", 200)

        json_response = json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False)
        return Response(json_response, status=status_code, content_type='application/json')

    except Exception as e:
        print(f"Error: {e}")
        response_data = OrderedDict([
            ("success", False),
            ("error", "Internal server error")
        ])
        json_response = json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False)
        return Response(json_response, status=500, content_type='application/json')


@app.route("/test_results/<test_id>/user/<user_id>", methods=["GET"])
@token_required
def get_student_test_results(test_id, user_id):
    try:
        service = CourseService()
        teacher_id = request.user.get("user_id")
        teacher_role = request.user.get("role")

        if teacher_role not in ["lecturer", "seminarist"]:
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        user_exists = service.check_user_exists(user_id)
        if not user_exists:
            response_data = {"error": "User not found", "status": 404}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                404,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.get_student_test_results(teacher_id, teacher_role, test_id, user_id)

        if isinstance(result, dict) and "error" in result:
            return make_response(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
                result.get("status", 400),
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        response_data = {
            "data": result if result else {},
            "status": 200
        }
        return make_response(
            json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
            200,
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

        if teacher_role not in ["lecturer", "seminarist"]:
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        data = request.get_json()
        if not data or not isinstance(data, list):
            response_data = {"error": "Invalid request format", "status": 400}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.update_student_test_results(teacher_id, teacher_role, test_id, user_id, data)
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


@app.route("/units/<int:unit_id>", methods=["POST"])
@token_required
def update_unit_content(unit_id):
    try:
        service = CourseService()
        teacher_id = request.user.get("user_id")
        teacher_role = request.user.get("role")

        if teacher_role not in ["lecturer", "seminarist"]:
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        data = request.get_json()
        if not data or "content" not in data:
            response_data = {"error": "Content is required", "status": 400}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        result = service.update_unit_content(teacher_id, teacher_role, unit_id, data["content"])
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


@app.route("/tests", methods=["POST"])
@token_required
def create_test():
    try:
        service = CourseService()
        user_id = request.user.get("user_id")
        user_role = request.user.get("role")

        if user_role not in ["lecturer", "seminarist"]:
            response_data = {"error": "Access denied", "status": 403}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                403,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

        data = request.get_json()
        if not data or "questions" not in data or "answers" not in data:
            response_data = {"error": "Questions and answers are required", "status": 400}
            return make_response(
                json.dumps(response_data, ensure_ascii=False, indent=2, sort_keys=False),
                400,
                {'Content-Type': 'application/json; charset=utf-8'}
            )

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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
