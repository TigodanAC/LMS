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

1. User Login
```
curl -X POST "http://localhost:8090/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "aivanov@college.ru", "password": "12345678"}'
```

2. Refresh Access Token
```
curl -X POST "http://localhost:8090/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJ..."}'
```

3. Create New Course (admin only)
```
curl -X POST "http://localhost:8091/courses" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый курс",
    "description": "Для проверки",
    "lector_id": "10",
    "groups": [
      {"group_id": "223-1", "seminarist_id": "4"},
      {"group_id": "233-1", "seminarist_id": "2"}
    ]
  }'
```

4. Get All Courses  
```
curl -X GET "http://localhost:8091/courses" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

With search:
```
curl -X GET "http://localhost:8091/courses" \
  -G \
  --data-urlencode "search=математика" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

5. Get Student Courses (admin only)
```
curl -X GET "http://localhost:8091/courses?student_id=2"   -H "Authorization: Bearer eyJhbGciOiJ..."
```

6. Get Course Details  
```
curl -X GET "http://localhost:8091/courses/MATH101" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

7. Update Course (admin/lecturer)  
```
curl -X PUT http://localhost:8091/courses/COURSE001 \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Дискретная математика",
    "description": "Изучение логики, теории множеств, графов, комбинаторики и их фундаментальной роли в компьютерных науках и алгоритмах",
    "groups": [
      {"group_id": "223-1", "seminarist_id": "2"},
      {"group_id": "223-2", "seminarist_id": "4"}
    ]
  }'
```

8. Create Block (teacher only)  
```
curl -X POST http://localhost:8091/courses/COURSE001/blocks \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Теория графов"
  }'
```

9. Get Block  
```
curl -X GET http://localhost:8091/blocks/block1_course001 \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

10. Update Block (teacher only)  
```
curl -X PUT http://localhost:8091/blocks/block2_course001 \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Основы множеств"
  }'
```

11. Create Unit (teacher only)  
```
curl -X POST http://localhost:8091/blocks/block1_course001/units \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Логические операторы",
    "type": "lecture",
    "content": "Материал о логических операторах: И, ИЛИ, НЕ"
  }'
```

12. Get Unit  
```
curl -X GET "http://localhost:8091/units/1" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

13. Update Unit (teacher only)  
```
curl -X PUT http://localhost:8091/units/28 \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Логические операторы (обновлено)",
    "content": "Обновленный материал о логических операторах"
  }'
```

14. Create Test (teacher only)
```
curl -X POST "http://localhost:8091/tests" \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
        {
            "id": 1,
            "text": "Какая из этих функций непрерывна на всей числовой прямой?",
            "type": "one_of",
            "answers": ["sin(x)", "1/x", "tan(x)", "1/(x^2)"]
        },
        {
            "id": 2,
            "text": "Какие из этих функций дифференцируемы везде?",
            "type": "many",
            "answers": ["x^2", "|x|", "e^x", "ln(x)"]
        },
        {
            "id": 3,
            "text": "Введите производную функции f(x) = x^2 + 3x - 5",
            "type": "custom",
            "answers": []
        }
    ],
    "answers": [
        {"id": 1, "answer": ["sin(x)"]},
        {"id": 2, "answer": ["x^2", "e^x"]},
        {"id": 3, "answer": []}
    ],
    "deadline": "2025-05-20 23:59:59"
  }'

```

15. Submit Test Results  
```
curl -X POST "http://localhost:8091/test_results/test1" \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '[{"id": 1, "answer": ["Медианa", "Среднее арифметическое", "Мода"]}, {"id": 2, "answer": ["Гистограммa"]}, {"id": 3, "answer": ["(x₁ + x₂ + ... + xₙ)/n"]}, {"id": 4, "answer": ["Дисперсия"]}]'
```

16. Get Test or Results
```
curl -X GET "http://localhost:8091/tests/test1" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

17. Get Student Test Results (teachers only)
```
curl -X GET "http://localhost:8091/test_results/test1/user/5"   -H "Authorization: Bearer eyJhbGciOiJ..."
```

18. Grade Test Manually (teachers only)
```
curl -X POST "http://localhost:8091/test_results/test1/user/15" \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '[{"id": 1, "is_right": true}, {"id": 2, "is_right": true}, {"id": 3, "is_right": true}, {"id": 4, "is_right": false}]'
```

19. Submit SOP Feedback  
```
curl -X POST "http://localhost:8091/sop" \
  -H "Authorization: Bearer eyJhbGciOiJ..." \
  -H "Content-Type: application/json" \
  -d '[
    {
      "course_id": "MATH101",
      "blocks": [
        {
          "block_type": "course",
          "teacher_id": "None",
          "questions_answers": [
            {"question": "Организация", "answer": 5},
            {"question": "Сложность", "answer": 3}
          ]
        },
        {
          "block_type": "lecturer",
          "teacher_id": "2",
          "questions_answers": [
            {"question": "Знание предмета", "answer": 2},
            {"question": "Пунктуальность", "answer": 4}
          ]
        },
        {
          "block_type": "seminarist",
          "teacher_id": "4",
          "questions_answers": [
            {"question": "Практические задания", "answer": 3},
            {"question": "Помощь", "answer": 5}
          ]
        }
      ]
    }]'
```

20. Get Teacher SOP Results (teachers only)
```
curl -X GET "http://localhost:8091/sop/teacher_results" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

21. Get Teacher SOP Results (admin only)  
```
curl -X GET "http://localhost:8091/sop/teacher_results?teacher_id=1" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

22. Get Course SOP Results  
```
curl -X GET "http://localhost:8091/sop/course_results/MATH101" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

23. Get Course Students  
```
curl -X GET "http://localhost:8091/courses/MATH101/students" \
  -H "Authorization: Bearer eyJhbGciOiJ..."
```

## Database Verification
The system uses PostgreSQL as its primary database. You can directly inspect data using the second terminal (where you accessed the database). Run the following commands:

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

## Running Tests
To execute the test suite, use the following command:
```
python3 -m pytest tests/ -v
```
