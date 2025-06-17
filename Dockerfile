# Railway Configuration for Maximum OCR Mortgage Analyzer

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for OCR
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/

