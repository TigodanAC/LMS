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


@app.route("/rate", methods=["POST"])
@token_required
def rate_course():
    data = request.get_json()
    if not data or "subject" not in data or "rating" not in data:
        return make_response("Missing required parameters", 400)

    try:
        rating = int(data["rating"])
        if not (1 <= rating <= 5):
            raise ValueError
    except ValueError:
        return make_response("Invalid rating value", 400)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ratings 
            (student_username, subject, rating)
            VALUES (%s, %s, %s)
        ''', (request.user["username"], data["subject"], rating))
        conn.commit()
        return make_response({"message": "Rating added successfully"}, 201)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return make_response("Internal server error", 500)
    finally:
        conn.close()


@app.route("/my_courses", methods=["GET"])
@token_required
def get_my_courses():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT subject, rating, created_at 
            FROM ratings 
            WHERE student_username = %s 
            ORDER BY created_at DESC
        ''', (request.user["username"],))
        results = [dict(row) for row in cursor.fetchall()]
        return make_response(json.dumps(results), 200)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
