FROM python:3.12-slim

WORKDIR /app

COPY docker/requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY ../src /app

#TODO: replace "main.py" with actual script file name when script is done
CMD ["python", "main.py"]