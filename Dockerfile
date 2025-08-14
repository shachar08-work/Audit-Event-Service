FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install build tools and libraries for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# COPY the AuditEventService folder into /app
COPY . .

EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
