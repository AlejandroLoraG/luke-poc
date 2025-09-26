FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose MCP server port
EXPOSE 8002

# Set environment variables
ENV PYTHONPATH=/app
ENV MCP_SERVER_PORT=8002

# Run the MCP server
CMD ["python", "src/server.py"]