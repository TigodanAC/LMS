from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError
import os
import time
from .models import Base

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:qwerty@db:5432/college')


def wait_for_db():
    engine = create_engine(DATABASE_URL)
    attempts = 0
    while attempts < 10:
        try:
            engine.connect()
            return True
        except OperationalError:
            time.sleep(2)
            attempts += 1
    raise Exception("Could not connect to database after 10 attempts")


def init_db():
    wait_for_db()
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("users"):
            Base.metadata.create_all(bind=engine)
            print("Database tables created successfully")
        else:
            print("Database tables already exist")


if __name__ == "__main__":
    init_db()

engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
