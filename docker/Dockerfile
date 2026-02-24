FROM python:3.12-slim

WORKDIR /app

COPY docker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src
COPY tests/ ./tests

CMD ["uvicorn", "src.normalizer_api:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]