# Minimal image for running the FastAPI backend + static frontend.
# 3.12-slim is used deliberately over a newer Python: it's a well-established
# base with broad availability, safely inside this project's 3.10+ support
# range (see README) -- not chasing the newest interpreter for its own sake.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
