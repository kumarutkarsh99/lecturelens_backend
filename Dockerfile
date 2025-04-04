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

# 🔹 Fix: Download required NLTK data (including punkt_tab)
RUN python -c "import nltk; \
    nltk.download('punkt'); \
    nltk.download('punkt_tab'); \
    nltk.download('stopwords'); \
    nltk.download('averaged_perceptron_tagger'); \
    nltk.download('wordnet');"

# Set Tesseract and Poppler paths
ENV TESSERACT_CMD="/usr/bin/tesseract"
ENV POPPLER_PATH="/usr/bin"

# Expose the port (default, Railway will set PORT dynamically)
EXPOSE 8080

# Use Gunicorn to run the Flask app with dynamic port binding (shell form for env var substitution)
CMD gunicorn -b 0.0.0.0:${PORT:-8080} app:app
