# Optional single-image stub (compose uses python slim + bind mount for W0).
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "mock_bank.app:app", "--host", "0.0.0.0", "--port", "8000"]
