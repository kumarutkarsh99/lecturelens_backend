# Use an official Python image as the base
FROM python:3.10-slim

# Set a non-interactive frontend to prevent prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Tesseract and Poppler paths
ENV TESSERACT_CMD="/usr/bin/tesseract"
ENV POPPLER_PATH="/usr/bin"

# Expose the Flask port
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
