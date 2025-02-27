FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY auth_service.py .
COPY signature.pem /tmp/signature.pem
COPY signature.pub /tmp/signature.pub
ENV JWT_PRIVATE_KEY_FILE=/tmp/signature.pem
ENV JWT_PUBLIC_KEY_FILE=/tmp/signature.pub
ENTRYPOINT ["python", "auth_service.py"]
CMD ["--private", "/tmp/signature.pem", "--public", "/tmp/signature.pub", "--port", "8090"]
