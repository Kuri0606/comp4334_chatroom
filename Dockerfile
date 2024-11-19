# Use the official Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies to install mysqlclient
# -y confirmed
# gcc - compiler
# default-libmysqlclient-dev - mysql library
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]