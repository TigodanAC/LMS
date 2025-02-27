FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY course_service.py .
COPY database ./database
COPY signature.pub /tmp/signature.pub
ENV JWT_PUBLIC_KEY_FILE=/tmp/signature.pub
ENTRYPOINT ["python", "course_service.py"]
CMD ["--public", "/tmp/signature.pub", "--port", "8091"]
