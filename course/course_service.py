from flask import Flask, request, make_response
import jwt
import os
import json
import psycopg2
from psycopg2.extras import DictCursor
from functools import wraps

app = Flask(__name__)

JWT_ALGORITHM = "RS256"
PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_FILE', '/tmp/signature.pub')

with open(PUBLIC_KEY_PATH, 'rb') as key_file:
    public_key = key_file.read()


def get_db_connection():
    return psycopg2.connect(
        dbname="college",
        user="postgres",
        password="qwerty",
        host="db",
        port=5432
    )


def decode_jwt(token):
    return jwt.decode(token, public_key, algorithms=JWT_ALGORITHM)


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


@app.route("/sop", methods=["POST"])
@token_required
def submit_sop():
    data = request.get_json()
    required_fields = [
        "course_id", "lecturer_feedback", "lecturer_clarity", "lecturer_requirements",
        "lecturer_communication", "seminarist_feedback", "seminarist_clarity",
        "seminarist_requirements", "seminarist_communication"
    ]

    if not all(field in data for field in required_fields):
        return make_response("Missing required fields", 400)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sop_responses 
            (student_username, course_id, lecturer_feedback, lecturer_clarity, 
             lecturer_requirements, lecturer_communication, seminarist_feedback, 
             seminarist_clarity, seminarist_requirements, seminarist_communication)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            request.user["username"],
            data["course_id"],
            data["lecturer_feedback"],
            data["lecturer_clarity"],
            data["lecturer_requirements"],
            data["lecturer_communication"],
            data["seminarist_feedback"],
            data["seminarist_clarity"],
            data["seminarist_requirements"],
            data["seminarist_communication"]
        ))
        conn.commit()
        return make_response({"message": "SOP response submitted successfully"}, 201)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return make_response("Internal server error", 500)
    finally:
        conn.close()


@app.route("/courses", methods=["GET"])
@token_required
def get_student_courses():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT c.id, c.subject, t1.last_name AS lecturer_last_name, 
                   t1.first_name AS lecturer_first_name, 
                   t2.last_name AS seminarist_last_name, 
                   t2.first_name AS seminarist_first_name
            FROM courses c
            JOIN teachers t1 ON c.lecturer_id = t1.id
            JOIN teachers t2 ON c.seminarist_id = t2.id
            WHERE c.group_number = (
                SELECT group_number FROM users WHERE username = %s
            )
        ''', (request.user["username"],))
        courses = [dict(row) for row in cursor.fetchall()]
        response = make_response(json.dumps(courses, ensure_ascii=False), 200)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()


@app.route("/sop/<int:course_id>", methods=["GET"])
@token_required
def get_sop_for_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT * FROM sop_responses 
            WHERE student_username = %s AND course_id = %s
        ''', (request.user["username"], course_id))
        sop_response = cursor.fetchone()
        if not sop_response:
            return make_response("No SOP response found for this course", 404)
        return make_response(json.dumps(dict(sop_response), ensure_ascii=False), 200)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
