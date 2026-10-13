FROM python:3.11-slim

WORKDIR /train

COPY requirements.txt . 

RUN pip install --no-cache-dir -r requirements.txt

COPY main-train.py .

CMD ["python", "main-train.py"]
