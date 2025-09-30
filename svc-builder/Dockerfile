FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY svc-builder/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared package and install in development mode
COPY shared/ ./shared/
COPY pyproject.toml .
RUN pip install -e .

# Copy application code
COPY svc-builder/app/ ./app/

# Create storage directory
RUN mkdir -p storage/workflows

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV SERVICE_PORT=8000

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]