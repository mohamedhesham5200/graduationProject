FROM python:3.9-slim

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gnupg2 \
    unixodbc-dev \
    libgomp1 \
    libc6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver for SQL Server with retries
RUN curl --retry 3 --retry-delay 5 https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl --retry 3 --retry-delay 5 https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql17 \
    mssql-tools18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Python version
RUN python --version

# Set working directory
WORKDIR /code

# Set permissions for /code to allow writing
RUN chown -R 1000:1000 /code && chmod -R 775 /code

# Upgrade pip to the latest version
RUN pip install --no-cache-dir --upgrade pip

# Copy and install Python dependencies with verbose output and retries
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 5 --verbose -r requirements.txt || { find /tmp -name 'pip*.log' -exec cat {} \; ; echo "Pip install failed"; exit 1; }

# Copy application code
COPY . .

# Ensure app directory is in Python path
ENV PYTHONPATH=/code

# Set environment variables for SQL Server
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV ACCEPT_EULA=Y

# Expose port for FastAPI
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]