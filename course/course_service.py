from database.database import init_db

init_db()

from flask import Flask, request, make_response
import jwt
import os
import json
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

JWT_ALGORITHM = "RS256"
PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_FILE', '/tmp/signature.pub')

with open(PUBLIC_KEY_PATH, 'rb') as key_file:
    public_key = key_file.read()

DATABASE = "college.db"


def get_db_connection():
    conn = psycopg2.connect(
        dbname="college",
        user="postgres",
        password="qwerty",
        host="db",
        port=5432
    )
    conn.cursor_factory = DictCursor
    return conn


def decode_jwt(token):
    return jwt.decode(token, public_key, algorithms=JWT_ALGORITHM)


def is_valid(token):
    if not token:
        return False, "Missing token"
    try:
        payload = decode_jwt(token)
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except jwt.InvalidTokenError:
        return False, "Invalid token"


@app.route("/rate", methods=["POST"])
def rate_course():
    token = request.cookies.get("jwt")
    is_token_valid, result = is_valid(token)
    if not is_token_valid:
        return make_response(result, 400 if result == "Token expired" or result == "Invalid token" else 401)
    payload = result
    username = payload["username"]
    subject = request.args.get("subject")
    rating = request.args.get("rating")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO ratings (student_username, subject, rating)
    VALUES (%s, %s, %s)
    ''', (username, subject, rating))
    conn.commit()
    conn.close()

    return make_response("Rating added", 200)


@app.route("/my_courses", methods=["GET"])
def get_my_courses():
    token = request.cookies.get("jwt")
    is_token_valid, result = is_valid(token)
    if not is_token_valid:
        return make_response(result, 400 if result == "Token expired" or result == "Invalid token" else 401)
    payload = result
    username = payload["username"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT subject, rating FROM ratings WHERE student_username = %s
    ''', (username,))
    courses = cursor.fetchall()
    conn.close()

    return make_response(json.dumps([dict(course) for course in courses]), 200)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8091)
