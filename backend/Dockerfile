FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  default-libmysqlclient-dev \
  build-essential \
  pkg-config \
  curl \
  default-mysql-client \
  netcat-traditional \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir wheel setuptools && \
  pip install --no-cache-dir -r requirements.txt

# Copy wait-for-it script first and make it executable
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Copy the rest of the application
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p logs uploads && \
  chmod -R 777 logs uploads

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=1

# Expose port
EXPOSE 5000

# Run the application with debug output
CMD ["/wait-for-it.sh", "db", "flask", "run", "--host=0.0.0.0", "--debug"] 