import psycopg2
from psycopg2 import sql, Error


def create_database(db_name, user, password, host='db', port='5432'):
    try:
        conn = psycopg2.connect(
            database="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}")
            .format(sql.Literal(db_name))
        )
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}")
                .format(sql.Identifier(db_name))
            )
            print(f"Database {db_name} created successfully")

        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error creating database: {e}")


def initialize_database():
    database = "college"
    user = "postgres"
    password = "qwerty"

    create_database(database, user, password)


if __name__ == "__main__":
    initialize_database()
