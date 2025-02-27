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


def create_tables(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                last_name VARCHAR(100) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash BYTEA NOT NULL,  -- Изменено на BYTEA
                role VARCHAR(50) NOT NULL CHECK(role IN ('student', 'teacher', 'college_worker')),
                group_number VARCHAR(100)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_subjects (
                id SERIAL PRIMARY KEY,
                group_number VARCHAR(100) NOT NULL,
                subject VARCHAR(100) NOT NULL
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id SERIAL PRIMARY KEY,
                last_name VARCHAR(100) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                subject VARCHAR(100) NOT NULL,
                seminarist_last_name VARCHAR(100),
                seminarist_first_name VARCHAR(100),
                seminarist_middle_name VARCHAR(100),
                group_number VARCHAR(100)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_roles (
                id SERIAL PRIMARY KEY,
                last_name VARCHAR(100) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                subject VARCHAR(100) NOT NULL,
                group_number VARCHAR(100),
                role VARCHAR(50) NOT NULL CHECK(role IN ('lecturer', 'seminarist'))
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                student_username VARCHAR(100) NOT NULL,
                subject VARCHAR(100) NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                FOREIGN KEY (student_username) REFERENCES users(username)
            );
        ''')
        conn.commit()
    except Error as e:
        print(e)


def init_db():
    database = "college"
    user = "postgres"
    password = "qwerty"
    create_database(database, user, password)
    conn = create_connection(database, user, password)
    if conn is not None:
        create_tables(conn)
        conn.close()
    else:
        print("Error: Cannot create the database connection.")


if __name__ == "__main__":
    init_db()
