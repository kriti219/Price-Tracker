# Change v1.45.0-noble to v1.45.0-jammy
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Copy dependency structures
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Start FastAPI using Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port $PORT