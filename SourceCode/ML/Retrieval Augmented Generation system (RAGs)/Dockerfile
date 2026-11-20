FROM python:3.10-slim

# Install system dependencies for pyodbc and curl
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create cache directory for Hugging Face models and set permissions
RUN mkdir -p /app/cache && chmod -R 777 /app/cache

# Pre-download the sentence-transformers model to avoid runtime cache writes
ENV HF_HOME=/app/cache
ENV HF_HUB_CACHE=/app/cache
RUN pip install sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='/app/cache')"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY model.py .
COPY database.py .

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]