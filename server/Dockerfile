FROM python:3.11-slim

WORKDIR /server

COPY requirements.txt . 

RUN pip install --no-cache-dir -r requirements.txt

COPY main-server.py . 

EXPOSE 8000 

CMD ["python", "-m", "flask", "--app", "main-server", "run", "--host=0.0.0.0", "--port=8000"]

