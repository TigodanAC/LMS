CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash BYTEA NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    role VARCHAR(50),
    group_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
    id VARCHAR(10) PRIMARY KEY,
    subject VARCHAR(255) NOT NULL,
    progress REAL DEFAULT 0.0,
    group_number VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    course_id VARCHAR(10) REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    block_id INTEGER REFERENCES blocks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS sop_submissions (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    course_id VARCHAR(10) REFERENCES courses(id),
    responses JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
