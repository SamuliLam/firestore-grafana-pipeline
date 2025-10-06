FROM python:3.12-slim

WORKDIR /app

COPY docker/requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY ../src /app

#TODO: csv_to_sql.py with final version that uses firestore as datasource
CMD ["python", "main.py"]
