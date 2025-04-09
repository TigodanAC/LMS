from flask import Flask, request, make_response, jsonify, json
import jwt
import time
import os
from functools import wraps
from sqlalchemy.sql import text
from auth.service import AuthService
from database.session import SessionLocal

app = Flask(__name__)

JWT_ALGORITHM = "RS256"
ACCESS_EXP_DELTA_SECONDS = 3600
REFRESH_EXP_DELTA_SECONDS = 604800
PRIVATE_KEY_PATH = os.getenv('JWT_PRIVATE_KEY_FILE', '/app/configs/signature.pem')
PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_FILE', '/app/configs/signature.pub')

with open(PRIVATE_KEY_PATH, 'rb') as key_file:
    private_key = key_file.read()

with open(PUBLIC_KEY_PATH, 'rb') as key_file:
    public_key = key_file.read()


def generate_access_token(email: str, user_id: str, role: str) -> str:
    payload = {
        "email": email,
        "user_id": user_id,
        "role": role,
        "type": "access",
        "exp": int(time.time()) + ACCESS_EXP_DELTA_SECONDS
    }
    token = jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token.replace('\n', '')


def generate_refresh_token(email: str) -> str:
    payload = {
        "email": email,
        "type": "refresh",
        "exp": int(time.time()) + REFRESH_EXP_DELTA_SECONDS
    }
    token = jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token.replace('\n', '')


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return make_response("Email and password required", 400)

    try:
        auth_service = AuthService()
        user = auth_service.authenticate_user(data["email"], data["password"])
        if not user:
            return make_response("Invalid email or password", 401)

        access_token = generate_access_token(user.email, user.user_id, user.role)
        refresh_token = generate_refresh_token(user.email)

        auth_service.create_refresh_token_record(
            refresh_token,
            user.user_id,
            REFRESH_EXP_DELTA_SECONDS
        )

        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        response = make_response(json.dumps(response_data, indent=4, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        print(f"Error: {e}")
        return make_response("Internal server error", 500)


@app.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()
    if not data or 'refresh_token' not in data:
        return make_response("Refresh token required", 400)

    try:
        refresh_token = data['refresh_token'].replace('\n', '').strip()
        auth_service = AuthService()
        user = auth_service.validate_refresh_token(refresh_token)
        if not user:
            return make_response("Invalid or expired refresh token", 401)
        new_access_token = generate_access_token(user.email, str(user.user_id))

        return jsonify({
            "access_token": new_access_token
        }), 200

    except jwt.ExpiredSignatureError:
        return make_response("Refresh token expired", 401)
    except jwt.InvalidTokenError:
        return make_response("Invalid token", 401)
    except Exception as e:
        print(f"Error during refresh: {str(e)}")
        return make_response("Internal server error", 500)


if __name__ == "__main__":
    import time

    time.sleep(2)
    app.run(host='0.0.0.0', port=8090, debug=False)
