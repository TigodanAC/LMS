from flask import Flask, request, make_response
import jwt
import time
import bcrypt
import os
import json
import psycopg2
import datetime
from psycopg2.extras import DictCursor
from functools import wraps

app = Flask(__name__)

JWT_ALGORITHM = "RS256"
ACCESS_EXP_DELTA_SECONDS = 3600
REFRESH_EXP_DELTA_SECONDS = 604800
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


def generate_access_token(email):
    payload = {
        "email": email,
        "type": "access",
        "exp": int(time.time()) + ACCESS_EXP_DELTA_SECONDS
    }
    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)


def generate_refresh_token(email):
    payload = {
        "email": email,
        "type": "refresh",
        "exp": int(time.time()) + REFRESH_EXP_DELTA_SECONDS
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
            if payload.get('type') != 'access':
                return make_response("Invalid token type", 401)
            request.user = payload
        except jwt.ExpiredSignatureError:
            return make_response("Token expired", 401)
        except jwt.InvalidTokenError:
            return make_response("Invalid token", 401)
        return f(*args, **kwargs)

    return decorated


@app.route("/utils/generate-password-hash", methods=["POST"])
def generate_password_hash():
    """Временный эндпоинт для генерации хэша пароля (только для админов)"""
    data = request.get_json()
    if not data or 'password' not in data:
        return make_response("Password required", 400)

    hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    return make_response({"password_hash": hashed.decode('utf-8')}, 200)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return make_response("Email and password required", 400)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('''
            SELECT id, email, password_hash 
            FROM users 
            WHERE email = %s
        ''', (data["email"],))
        user = cursor.fetchone()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()

    if not user or not bcrypt.checkpw(data["password"].encode('utf-8'), user['password_hash'].tobytes()):
        return make_response("Invalid email or password", 401)

    access_token = generate_access_token(user['email'])
    refresh_token = generate_refresh_token(user['email'])

    expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=REFRESH_EXP_DELTA_SECONDS)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO refresh_tokens (token, user_id, expires_at)
            VALUES (%s, %s, %s)
        ''', (refresh_token, user['id'], expires_at))
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return make_response("Internal server error", 500)
    finally:
        conn.close()

    return make_response({
        "access_token": access_token,
        "refresh_token": refresh_token
    }, 200)


@app.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()
    if not data or 'refresh_token' not in data:
        return make_response("Refresh token required", 400)

    refresh_token = data['refresh_token']
    try:
        payload = decode_jwt(refresh_token)
        if payload.get('type') != 'refresh':
            raise jwt.InvalidTokenError

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT user_id, expires_at 
            FROM refresh_tokens 
            WHERE token = %s
        ''', (refresh_token,))
        token_record = cursor.fetchone()
        conn.close()

        if not token_record:
            raise jwt.InvalidTokenError

        if datetime.datetime.utcnow() > token_record['expires_at']:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM refresh_tokens WHERE token = %s', (refresh_token,))
            conn.close()
            return make_response("Refresh token expired", 401)

        new_access_token = generate_access_token(payload['email'])
        return make_response({"access_token": new_access_token}, 200)

    except jwt.ExpiredSignatureError:
        return make_response("Refresh token expired", 401)
    except jwt.InvalidTokenError:
        return make_response("Invalid refresh token", 401)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8090)
