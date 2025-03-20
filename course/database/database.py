import psycopg2
from psycopg2 import sql, Error


def create_database(db_name, user, password, host='db', port='5432'):
    try:
        conn = psycopg2.connect(database="postgres", user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"База данных {db_name} создана.")
        else:
            print(f"База данных {db_name} уже существует.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Ошибка при создании базы данных: {e}")


def create_connection(db_name, user, password, host='db', port='5432'):
    conn = None
    try:
        conn = psycopg2.connect(database=db_name, user=user, password=password, host=host, port=port)
        return conn
    except Error as e:
        print(e)
    return conn


def init_db():
    database = "college"
    user = "postgres"
    password = "qwerty"
    create_database(database, user, password)
    conn = create_connection(database, user, password)
    if conn is not None:
        conn.close()
    else:
        print("Error: Cannot create the database connection.")


if __name__ == "__main__":
    init_db()
