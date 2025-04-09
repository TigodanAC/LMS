import bcrypt
import sys


def generate_password_hash(password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <password>")
        return

    password = sys.argv[1]
    hashed_password = generate_password_hash(password)
    print(f"Password hash: {hashed_password}")


if __name__ == "__main__":
    main()
