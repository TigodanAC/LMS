# Learning Management System (LMS) for Universities
This repository contains a Learning Management System (LMS) designed for universities. Below are instructions on how to set up and use the system, as well as examples of available API requests.

## Prerequisites
Ensure you have the following installed on your machine: Docker, Docker Compose

## Terminal Setup
To effectively work with the LMS, you should have three terminals open simultaneously:

First terminal: Running the server with docker compose up --build.

Second terminal: Accessing the PostgreSQL database.

Third terminal: Executing curl requests to interact with the API.

## Getting Started
### Start the Application
In the first terminal, run the following command to build and start the application:
```
docker compose up --build
```

### Stop the Application
To stop the application, use the first terminal and run:
```
docker compose down
```

### Check Running Containers
To see the list of all containers, use the second terminal and run:

```
docker ps -a
```

### Access the Database
In the second terminal, access the PostgreSQL database with the following command:

```
docker exec -it lms-db-1 psql -U postgres -d college
```

## API Endpoints
Use the third terminal to interact with the API using curl commands.

1. User Signup

To register a new user, run:

```
curl -i -X POST -H "Content-Type: application/json" \
-d '{"first_name": "Alice", "last_name": "Smith", "username": "alice_s", "password": "password123", "role": "student", "group_number": "301"}' \
"http://localhost:8090/signup"
```

2. User Login

To authenticate a user, run:

```
curl -i -X POST -H "Content-Type: application/json" \
-d '{"username": "alice_s", "password": "password123"}' \
"http://localhost:8090/login"
```

3. Who Am I

To check the current user information, run:

```
curl -i -X GET "http://localhost:8090/whoami" \
  -H "Authorization: Bearer <your_jwt_token>"
```
Replace <your_jwt_token> with the actual token received during login.


## Database Verification
To verify that the user was created successfully, use the second terminal (where you accessed the database) and run the following commands:

### List Tables
To see all tables in the database:

```
\dt
```

### Select Data from a Table
To view data from a specific table (replace table_name with the actual table name):

```
SELECT * FROM table_name;
```

## Conclusion

This LMS provides a simple interface for user registration and authentication, and it uses JWT for secure token management. Ensure you follow the steps above to set up and interact with the system effectively