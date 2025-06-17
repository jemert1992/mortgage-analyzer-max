# Mortgage Package Analyzer - Local Server

A standalone web application for analyzing mortgage packages with full OCR capabilities.

## Features

- **🏠 Local Processing**: All files processed on your machine, never uploaded to external servers
- **🔍 Full OCR**: Handles both text-based and image-based PDFs
- **📊 Smart Analysis**: Identifies 15+ common mortgage document types
- **🎯 High Accuracy**: Enhanced pattern matching for mortgage-specific sections
- **💾 No Size Limits**: Process large mortgage packages without restrictions
- **🔒 Complete Privacy**: Documents never leave your computer

## Quick Start

### Prerequisites

1. **Python 3.8+** installed on your system
2. **System dependencies** (for OCR):
   - **Windows**: Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract poppler`
   - **Linux**: `sudo apt-get install tesseract-ocr poppler-utils`

### Installation

1. **Download** the application files to a folder
2. **Open terminal/command prompt** in that folder
3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

3. **Upload your mortgage package PDF** and analyze!

## Usage

1. **Upload PDF**: Drag and drop or click to browse for your mortgage package PDF
2. **Wait for Processing**: The application will extract text and identify sections
3. **Review Results**: Check identified sections with confidence levels
4. **Select Sections**: Choose which sections to include in your table of contents
5. **Generate TOC**: Download a formatted table of contents

## Supported Document Types

The analyzer can identify these common mortgage document sections:

- Mortgage/Deed of Trust
- Promissory Note
- Settlement Statement
- Lenders Closing Instructions
- Title Policy/Insurance
- Flood Hazard Determination
- Insurance Policies
- Tax Records
- Automatic Payment Authorization
- Anti-Coercion Statements
- Power of Attorney documents
- Acknowledgments and Affidavits
- UCC Filings
- Signature Pages

## Technical Details

- **Framework**: Flask (Python web framework)
- **PDF Processing**: pdfplumber for text extraction
- **OCR Engine**: Tesseract for image-based PDFs
- **Image Processing**: pdf2image + Pillow
- **Interface**: Modern HTML5/CSS3/JavaScript

## Troubleshooting

### OCR Not Working
- Ensure Tesseract is installed and in your system PATH
- On Windows, you may need to set the tesseract path in the code

### Large Files Slow
- Large PDFs with many images take longer to process
- Progress bar shows current status
- Consider processing smaller sections if needed

### Dependencies Issues
- Make sure all requirements are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

## Privacy & Security

- **Local Processing**: All files are processed on your local machine
- **No External Uploads**: Documents never leave your computer
- **No Data Storage**: Files are not saved after processing
- **Secure**: No network dependencies for document processing

## Support

This is a standalone application designed for local use. All processing happens on your machine for maximum privacy and security.

---

**Version**: 1.0 Local  
**License**: For personal/business use  
**Privacy**: 100% Local Processing

