FROM python:3.12-slim

WORKDIR /app

COPY docker/requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "history_to_timescale.py"]