FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY ai-agent/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared package and install in development mode
COPY shared/ ./shared/
COPY pyproject.toml .
RUN pip install -e .

# Copy source code
COPY ai-agent/src/ ./src/

# Expose port
EXPOSE 8001

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8001

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]