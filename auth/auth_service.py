from flask import Flask, request, make_response
import jwt
import time
import bcrypt
import os
import json
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

JWT_ALGORITHM = "RS256"
JWT_EXP_DELTA_SECONDS = 3600
PRIVATE_KEY_PATH = os.getenv('JWT_PRIVATE_KEY_FILE', '/tmp/signature.pem')
PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_FILE', '/tmp/signature.pub')

with open(PRIVATE_KEY_PATH, 'rb') as key_file:
    private_key = key_file.read()

with open(PUBLIC_KEY_PATH, 'rb') as key_file:
    public_key = key_file.read()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:qwerty@localhost:5433/college')


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def generate_jwt(username):
    payload = {
        "username": username,
        "exp": int(time.time()) + JWT_EXP_DELTA_SECONDS
    }
    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)


def decode_jwt(token):
    return jwt.decode(token, public_key, algorithms=JWT_ALGORITHM)


@app.route("/signup", methods=["POST"])
def signup():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.data.decode('utf-8')
        data = json.loads(data)
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    middle_name = data.get("middle_name")
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")
    group_number = data.get("group_number")

    if not all([first_name, last_name, username, password, role]):
        return make_response("Missing required fields", 400)

    if role == "student" and not group_number:
        return make_response("Group number is required for students", 400)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return make_response("User already exists", 403)

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (last_name, first_name, middle_name, username, password_hash, role, group_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (last_name, first_name, middle_name, username, password_hash, role, group_number))
        cursor.execute("COMMIT")
    except psycopg2.Error as e:
        print(f"Ошибка при выполнении SQL-запроса: {e}")
        conn.rollback()
        return make_response("Internal Server Error", 500)
    finally:
        conn.close()

    token = generate_jwt(username)
    response = make_response(json.dumps({"message": "User created", "token": token}), 200)
    return response


@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.data.decode('utf-8')
        data = json.loads(data)
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return make_response("Invalid username or password", 403)

    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].tobytes()):
        return make_response("Invalid username or password", 403)

    token = generate_jwt(username)
    response = make_response(json.dumps({"message": "User logged in", "token": token}), 200)
    return response


@app.route("/whoami", methods=["GET"])
def whoami():
    token = request.cookies.get("jwt")
    if not token:
        return make_response("Missing token", 401)
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return make_response("Token expired", 400)
    except jwt.InvalidTokenError:
        return make_response("Invalid token", 400)

    username = payload["username"]
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return make_response("User does not exist", 400)
    return make_response(f"Hello, {username}", 200)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8090)
