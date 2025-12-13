# Use the official Python base image
FROM python:3.11-slim

# Set environment variables to optimize Python performance in a container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Django project files
COPY . /app

# Set the entry point command (this will be overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]