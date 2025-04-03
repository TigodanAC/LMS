from flask import Flask, request, make_response, jsonify
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


@app.route("/api/courses", methods=["GET"])
@token_required
def get_courses():
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)
    search = request.args.get('search', default='', type=str)
    search_pattern = f"%{search}%" if search else "%"

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        cursor.execute("SELECT group_number FROM users WHERE email = %s", (request.user["email"],))
        user_group = cursor.fetchone()["group_number"]
        cursor.execute("""
            SELECT id, subject AS name, progress 
            FROM courses 
            WHERE 
                group_number = %s AND
                subject ILIKE %s
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (user_group, search_pattern, limit, offset))

        courses = [dict(row) for row in cursor.fetchall()]
        response = make_response(json.dumps(courses, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()


@app.route("/api/courses/<course_id>", methods=["GET"])
@token_required
def get_course_details(course_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute("""
            SELECT c.id, c.subject AS name
            FROM courses c
            WHERE c.id = %s 
            AND c.group_number = (
                SELECT group_number FROM users WHERE email = %s
            )
        """, (course_id, request.user["email"]))
        course = cursor.fetchone()
        if not course:
            return make_response("Course not found or access denied", 404)
        course_data = dict(course)

        cursor.execute("""
            SELECT id, name 
            FROM blocks 
            WHERE course_id = %s
            ORDER BY id
        """, (course_id,))
        blocks = []
        for block in cursor.fetchall():
            block_dict = dict(block)
            cursor.execute("""
                SELECT id, name, status
                FROM units
                WHERE block_id = %s
                ORDER BY id
            """, (block['id'],))
            units = [dict(unit) for unit in cursor.fetchall()]
            block_dict["units"] = units
            blocks.append(block_dict)
        course_data["blocks"] = blocks

        response = make_response(json.dumps(course_data, ensure_ascii=False), 200)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()


@app.route("/sop", methods=["POST"])
@token_required
def submit_sop():
    """
    Принимает JSON-объект, содержащий:
      - course_id: идентификатор курса (должен существовать в БД)
      - blocks: список блоков с вопросами и ответами
    """
    data = request.get_json()
    if not data:
        return make_response("Empty request body", 400)

    if "course_id" not in data or "blocks" not in data or not isinstance(data["blocks"], list):
        return make_response("Missing required fields: course_id and blocks", 400)

    email = request.user["email"]
    course_id = data["course_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM courses WHERE id = %s LIMIT 1', (course_id,))
        if not cursor.fetchone():
            return make_response(
                json.dumps({"error": "Course not found"}, ensure_ascii=False),
                404
            )
        cursor.execute('''
            SELECT 1 FROM sop_submissions 
            WHERE email = %s AND course_id = %s
            LIMIT 1
        ''', (email, course_id))

        if cursor.fetchone():
            return make_response(
                json.dumps({"error": "SOP already submitted for this course"}, ensure_ascii=False),
                409
            )
        submission_data = {
            "blocks": data["blocks"]
        }
        cursor.execute('''
            INSERT INTO sop_submissions 
            (email, course_id, responses)
            VALUES (%s, %s, %s)
        ''', (
            email,
            course_id,
            json.dumps(submission_data, ensure_ascii=False)
        ))

        conn.commit()
        return make_response(
            json.dumps({"message": "SOP submission saved successfully"}, ensure_ascii=False),
            201
        )

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return make_response("Internal server error", 500)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
