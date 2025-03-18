from flask import Flask, request, make_response
import jwt
import time
import bcrypt
import os
import json
import psycopg2
from psycopg2.extras import DictCursor
from functools import wraps

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


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() if request.is_json else json.loads(request.data)

    required_fields = ["first_name", "last_name", "username", "password", "role"]
    if not all(data.get(field) for field in required_fields):
        return make_response("Missing required fields", 400)

    if data["role"] == "student" and not data.get("group_number"):
        return make_response("Group number required for students", 400)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute("SELECT username FROM users WHERE username = %s", (data["username"],))
        if cursor.fetchone():
            return make_response("Username already exists", 409)

        hashed_pw = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users 
            (last_name, first_name, middle_name, username, password_hash, role, group_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data["last_name"],
            data["first_name"],
            data.get("middle_name"),
            data["username"],
            hashed_pw,
            data["role"],
            data.get("group_number")
        ))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()

    token = generate_jwt(data["username"])
    response = make_response({"message": "User created successfully"}, 201)
    response.headers['Authorization'] = f"Bearer {token}"
    return response


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() if request.is_json else json.loads(request.data)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT username, password_hash 
            FROM users 
            WHERE username = %s
        ''', (data["username"],))
        user = cursor.fetchone()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()

    if not user or not bcrypt.checkpw(data["password"].encode('utf-8'), user['password_hash'].tobytes()):
        return make_response("Invalid credentials", 401)

    token = generate_jwt(data["username"])
    response = make_response({"message": "Login successful"}, 200)
    response.headers['Authorization'] = f"Bearer {token}"
    return response


@app.route("/whoami", methods=["GET"])
@token_required
def whoami():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT first_name, last_name, role 
            FROM users 
            WHERE username = %s
        ''', (request.user["username"],))
        user = cursor.fetchone()
        if not user:
            return make_response("User not found", 404)
        return make_response(json.dumps(dict(user)), 200)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8090)
