# Use an official Python runtime as a base image
FROM python:3.10

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc\
    python3-dev \
    default-libmysqlclient-dev \
    libpq-dev
# Set the working directory in the container
WORKDIR /app



COPY . /app/
RUN pip install --upgrade pip wheel setuptools
RUN pip install .

# Start the Flask application when the container starts
CMD ["python", "app.py"]