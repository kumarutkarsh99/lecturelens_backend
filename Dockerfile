FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import nltk; \
    nltk.download('punkt'); \
    nltk.download('punkt_tab'); \
    nltk.download('stopwords'); \
    nltk.download('averaged_perceptron_tagger'); \
    nltk.download('wordnet');"

ENV TESSERACT_CMD="/usr/bin/tesseract"
ENV POPPLER_PATH="/usr/bin"

EXPOSE 8080

CMD gunicorn -b 0.0.0.0:${PORT:-8080} app:app
