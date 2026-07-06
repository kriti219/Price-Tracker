# Use the official Microsoft Playwright image that includes Python and browser binaries
FROM mcr.microsoft.com/playwright/python:v1.45.0-noble

WORKDIR /app

# Copy dependency structures
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Railway provides dynamically
EXPOSE 8000

# Start FastAPI using Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]