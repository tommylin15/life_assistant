FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run must begin listening promptly. Schema migrations stay versioned
# and CI-validated, while the FastAPI startup safety net creates additive
# tables until migrations are moved to a dedicated VPC-capable runner/job.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
