#!/usr/bin/env python3
"""
Standalone Mortgage Package Analyzer
Local Web Server Version

This application runs locally on your machine and provides:
- Full OCR capabilities with tesseract
- Large file processing (no size limits)
- Complete privacy (no external hosting)
- Professional mortgage document analysis

Usage:
    python app.py

Then open: http://localhost:5000
"""

import os
import sys
import io
import uuid
import hashlib
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# PDF processing imports
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not available")

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR dependencies not available")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'local-mortgage-analyzer-key'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB for local processing

# Enable CORS for local development
CORS(app)

# Global variables for progress tracking
progress_data = {}

def update_progress(session_id, current, total, status):
    """Update progress for a session"""
    progress_data[session_id] = {
        'current': current,
        'total': total,
        'status': status,
        'percentage': int((current / total) * 100) if total > 0 else 0,
        'timestamp': datetime.now().isoformat()
    }

def extract_text_from_pdf(file_content, session_id=None):
    """Extract text from PDF using multiple methods"""
    text_content = []
    
    print(f"[LOCAL] Starting PDF text extraction from {len(file_content)} bytes")
    
    # Method 1: Try pdfplumber first (fastest for text-based PDFs)
    if PDFPLUMBER_AVAILABLE:
        try:
            print("[LOCAL] Attempting pdfplumber extraction...")
            pdf_file = io.BytesIO(file_content)
            
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                print(f"[LOCAL] PDF has {total_pages} pages")
                
                if session_id:
                    update_progress(session_id, 0, total_pages, "extracting_text")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        if session_id:
                            update_progress(session_id, page_num, total_pages, "extracting_text")
                        
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                            for line in lines:
                                if len(line) > 3:  # Filter out very short lines
                                    text_content.append({
                                        "text": line,
                                        "page": page_num,
                                        "method": "pdfplumber"
                                    })
                            print(f"[LOCAL] Page {page_num}: extracted {len(lines)} lines via pdfplumber")
                    except Exception as e:
                        print(f"[LOCAL] pdfplumber failed on page {page_num}: {e}")
                        continue
            
            print(f"[LOCAL] pdfplumber extraction: {len(text_content)} text items")
            
        except Exception as e:
            print(f"[LOCAL] pdfplumber extraction failed: {e}")
    
    # Method 2: If little text extracted, try OCR
    if len(text_content) < 10 and OCR_AVAILABLE:
        print("[LOCAL] Low text yield, attempting OCR extraction...")
        
        try:
            # Convert PDF to images
            images = convert_from_bytes(file_content, dpi=150)
            total_pages = len(images)
            print(f"[LOCAL] Converted {total_pages} pages to images for OCR")
            
            if session_id:
                update_progress(session_id, 0, total_pages, "ocr_processing")
            
            ocr_text_content = []
            
            for page_num, image in enumerate(images, 1):
                try:
                    if session_id:
                        update_progress(session_id, page_num, total_pages, f"ocr_page_{page_num}")
                    
                    print(f"[LOCAL] Running OCR on page {page_num}/{total_pages}...")
                    
                    # Run OCR
                    text = pytesseract.image_to_string(image, lang='eng')
                    
                    if text.strip():
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        # Filter OCR noise
                        clean_lines = []
                        for line in lines:
                            if len(line) > 5 and any(c.isalpha() for c in line):
                                clean_lines.append(line)
                        
                        for line in clean_lines:
                            ocr_text_content.append({
                                "text": line,
                                "page": page_num,
                                "method": "OCR"
                            })
                        
                        if clean_lines:
                            print(f"[LOCAL] Page {page_num}: extracted {len(clean_lines)} clean lines via OCR")
                
                except Exception as e:
                    print(f"[LOCAL] OCR failed on page {page_num}: {e}")
                    continue
            
            if ocr_text_content:
                print(f"[LOCAL] OCR extraction successful: {len(ocr_text_content)} text items")
                text_content = ocr_text_content  # Use OCR results
            
        except Exception as e:
            print(f"[LOCAL] OCR extraction failed: {e}")
            traceback.print_exc()
    
    print(f"[LOCAL] Final extraction: {len(text_content)} text items from {len(set(item['page'] for item in text_content)) if text_content else 0} pages")
    
    return text_content

def analyze_mortgage_sections(text_content):
    """Analyze mortgage document sections using enhanced pattern matching"""
    
    # Enhanced rules based on real mortgage documents
    section_rules = [
        # Core mortgage documents (highest priority)
        {"patterns": ["MORTGAGE", "DEED OF TRUST", "SECURITY INSTRUMENT"], "label": "Mortgage", "priority": 10},
        {"patterns": ["PROMISSORY NOTE", "NOTE"], "label": "Promissory Note", "priority": 10},
        
        # Closing documents
        {"patterns": ["LENDERS CLOSING INSTRUCTIONS", "CLOSING INSTRUCTIONS GUARANTY", "LENDER'S CLOSING INSTRUCTIONS"], "label": "Lenders Closing Instructions Guaranty", "priority": 9},
        {"patterns": ["SETTLEMENT STATEMENT", "HUD-1", "CLOSING DISCLOSURE"], "label": "Settlement Statement", "priority": 9},
        
        # Legal documents
        {"patterns": ["STATEMENT OF ANTI COERCION", "ANTI COERCION", "ANTI-COERCION FLORIDA"], "label": "Statement of Anti Coercion Florida", "priority": 8},
        {"patterns": ["CORRECTION AGREEMENT", "LIMITED POWER OF ATTORNEY", "POWER OF ATTORNEY"], "label": "Correction Agreement and Limited Power of Attorney", "priority": 8},
        {"patterns": ["ALL PURPOSE ACKNOWLEDGMENT", "ACKNOWLEDGMENT", "NOTARY ACKNOWLEDGMENT"], "label": "All Purpose Acknowledgment", "priority": 8},
        
        # Insurance and hazard documents
        {"patterns": ["FLOOD HAZARD DETERMINATION", "FLOOD DETERMINATION", "FEMA FLOOD"], "label": "Flood Hazard Determination", "priority": 7},
        {"patterns": ["INSURANCE POLICY", "HOMEOWNER'S INSURANCE", "HAZARD INSURANCE"], "label": "Insurance Policy", "priority": 7},
        
        # Payment and tax documents
        {"patterns": ["AUTOMATIC PAYMENTS AUTHORIZATION", "AUTOMATIC PAYMENT", "ACH AUTHORIZATION"], "label": "Automatic Payments Authorization", "priority": 7},
        {"patterns": ["TAX RECORD INFORMATION", "TAX RECORDS", "PROPERTY TAX"], "label": "Tax Record Information", "priority": 7},
        
        # Title documents
        {"patterns": ["TITLE POLICY", "TITLE INSURANCE", "OWNER'S POLICY"], "label": "Title Policy", "priority": 6},
        {"patterns": ["DEED", "WARRANTY DEED", "QUITCLAIM DEED"], "label": "Deed", "priority": 6},
        
        # Other documents
        {"patterns": ["UCC FILING", "UCC-1", "FINANCING STATEMENT"], "label": "UCC Filing", "priority": 5},
        {"patterns": ["SIGNATURE PAGE", "SIGNATURES", "BORROWER SIGNATURE"], "label": "Signature Page", "priority": 5},
        {"patterns": ["AFFIDAVIT", "SWORN STATEMENT"], "label": "Affidavit", "priority": 5},
    ]
    
    found_sections = {}
    
    # Analyze each text item
    for item in text_content:
        text = item["text"].upper()
        page = item["page"]
        
        for rule in section_rules:
            patterns = rule["patterns"]
            label = rule["label"]
            priority = rule["priority"]
            
            for pattern in patterns:
                if pattern in text:
                    # Determine confidence
                    confidence = "medium"
                    if text.strip() == pattern:
                        confidence = "high"
                    elif pattern in text and len(text.split()) <= 10:
                        confidence = "high"
                    elif len([p for p in patterns if p in text]) > 1:
                        confidence = "high"
                    
                    # Keep best match for each section type
                    if label not in found_sections:
                        found_sections[label] = {
                            "section_type": label,
                            "page": page,
                            "confidence": confidence,
                            "text_snippet": item["text"][:100],
                            "priority": priority,
                            "pattern_matched": pattern
                        }
                        print(f"[LOCAL] Found section: {label} on page {page} (pattern: {pattern})")
                    else:
                        # Update if better match
                        existing = found_sections[label]
                        confidence_rank = {"high": 3, "medium": 2, "low": 1}
                        if (confidence_rank.get(confidence, 0) > confidence_rank.get(existing["confidence"], 0) or
                            (confidence == existing["confidence"] and priority >= existing["priority"])):
                            found_sections[label].update({
                                "page": page,
                                "confidence": confidence,
                                "text_snippet": item["text"][:100],
                                "pattern_matched": pattern
                            })
                    break
    
    # Sort by priority and page
    sections = sorted(list(found_sections.values()), 
                     key=lambda x: (-x["priority"], x["page"], x["section_type"]))
    
    print(f"[LOCAL] Analysis complete: {len(sections)} sections identified")
    return sections

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """Analyze uploaded mortgage document"""
    try:
        print("[LOCAL] Starting document analysis...")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        print(f"[LOCAL] Processing file: {file.filename} ({file_size} bytes)")
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Initialize progress
        update_progress(session_id, 0, 1, "starting")
        
        # Extract text from PDF
        text_content = extract_text_from_pdf(file_content, session_id)
        
        if not text_content:
            return jsonify({'error': 'Could not extract text from PDF. The file may be corrupted or contain only images without readable text.'}), 400
        
        # Analyze sections
        update_progress(session_id, 1, 1, "analyzing")
        sections = analyze_mortgage_sections(text_content)
        
        # Complete
        update_progress(session_id, 1, 1, "completed")
        
        print(f"[LOCAL] Analysis complete: {len(sections)} sections identified")
        
        return jsonify({
            'session_id': session_id,
            'sections': sections,
            'total_pages': len(set(item['page'] for item in text_content)),
            'total_text_items': len(text_content),
            'processing_method': 'local',
            'ocr_available': OCR_AVAILABLE,
            'pdfplumber_available': PDFPLUMBER_AVAILABLE
        })
        
    except Exception as e:
        error_msg = f"Document processing error: {str(e)}"
        print(f"[LOCAL ERROR] {error_msg}")
        print(f"[LOCAL ERROR] Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@app.route('/api/progress/<session_id>')
def get_progress(session_id):
    """Get processing progress for a session"""
    if session_id in progress_data:
        return jsonify(progress_data[session_id])
    else:
        return jsonify({'error': 'Session not found'}), 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': 'local-1.0',
        'ocr_available': OCR_AVAILABLE,
        'pdfplumber_available': PDFPLUMBER_AVAILABLE,
        'dependencies': {
            'pdfplumber': PDFPLUMBER_AVAILABLE,
            'pdf2image': OCR_AVAILABLE,
            'pytesseract': OCR_AVAILABLE
        }
    })

# HTML Template for the application
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mortgage Package Analyzer - Local</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
            color: white; 
            padding: 40px; 
            text-align: center; 
        }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
        .header p { margin: 15px 0 0 0; opacity: 0.9; font-size: 1.1em; }
        .status-bar {
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #28a745;
        }
        .section { 
            margin: 30px; 
            padding: 25px; 
            border: 1px solid #e0e0e0; 
            border-radius: 10px; 
            background: #fafafa;
        }
        .upload-area {
            border: 3px dashed #ccc;
            border-radius: 12px;
            padding: 60px;
            text-align: center;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9ff;
            transform: translateY(-2px);
        }
        .upload-area.dragover {
            border-color: #667eea;
            background: #f0f8ff;
        }
        .file-input { display: none; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            margin: 8px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
            transform: none;
            box-shadow: none;
        }
        .progress-container {
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            width: 0%;
            transition: width 0.3s ease;
        }
        .progress-text {
            text-align: center;
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
        .results { 
            margin-top: 30px; 
            display: none; 
        }
        .section-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .section-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .confidence-high { border-left: 4px solid #28a745; }
        .confidence-medium { border-left: 4px solid #ffc107; }
        .confidence-low { border-left: 4px solid #dc3545; }
        .section-title {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        .section-meta {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
        }
        .section-snippet {
            font-size: 12px;
            font-style: italic;
            color: #888;
            background: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .error { 
            background: #f8d7da; 
            color: #721c24; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0;
            border: 1px solid #f5c6cb;
        }
        .success { 
            background: #d4edda; 
            color: #155724; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0;
            border: 1px solid #c3e6cb;
        }
        .local-badge {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(40, 167, 69, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            backdrop-filter: blur(10px);
        }
    </style>
</head>
<body>
    <div class="local-badge">🏠 Local Server</div>
    
    <div class="container">
        <div class="header">
            <h1>🏠 Mortgage Package Analyzer</h1>
            <p>Local Web Server - Full OCR Capabilities - Complete Privacy</p>
        </div>

        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span>Local Server Running</span>
            </div>
            <div id="dependencyStatus">
                <span>Loading dependencies...</span>
            </div>
        </div>

        <div class="section">
            <h2>📄 Upload Mortgage Package</h2>
            <div class="upload-area" id="uploadArea">
                <h3>📁 Drop your PDF file here or click to browse</h3>
                <p>Supports large PDF files - no size limits on local processing</p>
                <p style="font-size: 12px; color: #666;">Files are processed locally and never leave your machine</p>
                <input type="file" id="fileInput" class="file-input" accept=".pdf">
            </div>
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">Processing...</div>
            </div>
        </div>

        <div class="results" id="results">
            <div class="section">
                <h2>📋 Identified Sections</h2>
                <div class="controls">
                    <button class="btn" onclick="selectAll()">Select All</button>
                    <button class="btn" onclick="selectNone()">Select None</button>
                    <button class="btn" onclick="selectHighConfidence()">Select High Confidence</button>
                    <button class="btn" onclick="generateTOC()">Generate Table of Contents</button>
                </div>
                <div class="section-grid" id="sectionsContainer">
                    <!-- Sections will be populated here -->
                </div>
            </div>
        </div>
    </div>

    <script>
        console.log('🏠 Local Mortgage Analyzer Loading...');
        
        let currentSections = [];
        let currentSessionId = null;

        document.addEventListener('DOMContentLoaded', function() {
            console.log('✅ Local version loaded successfully');
            setupEventListeners();
            checkDependencies();
        });

        function setupEventListeners() {
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');

            uploadArea.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', handleFileSelect);

            // Drag and drop
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', function() {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0]);
                }
            });
        }

        function checkDependencies() {
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    const status = document.getElementById('dependencyStatus');
                    if (data.ocr_available && data.pdfplumber_available) {
                        status.innerHTML = '<span style="color: #28a745;">✅ Full OCR Capabilities</span>';
                    } else if (data.pdfplumber_available) {
                        status.innerHTML = '<span style="color: #ffc107;">⚠️ Text Extraction Only</span>';
                    } else {
                        status.innerHTML = '<span style="color: #dc3545;">❌ Limited Capabilities</span>';
                    }
                })
                .catch(() => {
                    document.getElementById('dependencyStatus').innerHTML = '<span style="color: #dc3545;">❌ Server Error</span>';
                });
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                handleFile(file);
            }
        }

        function handleFile(file) {
            console.log('📄 Processing file:', file.name);
            
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                showError('Please select a PDF file.');
                return;
            }

            uploadAndAnalyze(file);
        }

        function uploadAndAnalyze(file) {
            console.log('🚀 Starting local analysis...');
            
            const formData = new FormData();
            formData.append('file', file);

            // Show progress
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            updateProgress(0, 'Starting analysis...');

            fetch('/api/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('📡 Response status:', response.status);
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error('HTTP ' + response.status + ': ' + JSON.stringify(err));
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('✅ Analysis response:', data);
                
                if (data.error) {
                    throw new Error(data.error);
                }

                currentSections = data.sections || [];
                currentSessionId = data.session_id;
                
                updateProgress(100, 'Analysis complete!');
                setTimeout(() => {
                    document.getElementById('progressContainer').style.display = 'none';
                    displayResults(currentSections, data);
                    showSuccess(`Analysis complete! Found ${currentSections.length} sections in ${data.total_pages} pages.`);
                }, 1000);
            })
            .catch(error => {
                console.error('❌ Analysis error:', error);
                document.getElementById('progressContainer').style.display = 'none';
                showError('Error analyzing document: ' + error.message);
            });
        }

        function updateProgress(percentage, text) {
            document.getElementById('progressFill').style.width = percentage + '%';
            document.getElementById('progressText').textContent = text;
        }

        function displayResults(sections, metadata) {
            console.log('📋 Displaying results:', sections);
            
            const container = document.getElementById('sectionsContainer');
            const resultsDiv = document.getElementById('results');
            
            if (!sections || sections.length === 0) {
                container.innerHTML = '<div class="error">No sections identified in the document.</div>';
                resultsDiv.style.display = 'block';
                return;
            }

            let html = '';
            sections.forEach((section, index) => {
                html += `
                    <div class="section-card confidence-${section.confidence}">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <input type="checkbox" id="section-${index}" checked>
                            <label for="section-${index}" class="section-title">${section.section_type}</label>
                        </div>
                        <div class="section-meta">
                            Page ${section.page} • ${section.confidence} confidence
                            ${section.pattern_matched ? ' • Pattern: "' + section.pattern_matched + '"' : ''}
                        </div>
                        <div class="section-snippet">
                            "${section.text_snippet}"
                        </div>
                    </div>
                `;
            });

            // Add metadata info
            html += `
                <div class="section-card" style="border-left: 4px solid #17a2b8;">
                    <div class="section-title">📊 Processing Summary</div>
                    <div class="section-meta">
                        Total Pages: ${metadata.total_pages} • 
                        Text Items: ${metadata.total_text_items} • 
                        OCR Available: ${metadata.ocr_available ? 'Yes' : 'No'} •
                        Method: ${metadata.processing_method}
                    </div>
                </div>
            `;

            container.innerHTML = html;
            resultsDiv.style.display = 'block';
        }

        function selectAll() {
            document.querySelectorAll('#sectionsContainer input[type="checkbox"]').forEach(cb => cb.checked = true);
        }

        function selectNone() {
            document.querySelectorAll('#sectionsContainer input[type="checkbox"]').forEach(cb => cb.checked = false);
        }

        function selectHighConfidence() {
            document.querySelectorAll('#sectionsContainer input[type="checkbox"]').forEach((cb, index) => {
                cb.checked = currentSections[index] && currentSections[index].confidence === 'high';
            });
        }

        function generateTOC() {
            const selectedSections = [];
            document.querySelectorAll('#sectionsContainer input[type="checkbox"]:checked').forEach((checkbox, index) => {
                const sectionIndex = parseInt(checkbox.id.split('-')[1]);
                if (currentSections[sectionIndex]) {
                    selectedSections.push(currentSections[sectionIndex]);
                }
            });

            if (selectedSections.length === 0) {
                showError('Please select at least one section.');
                return;
            }

            // Sort by page number
            selectedSections.sort((a, b) => a.page - b.page);

            // Generate professional TOC
            let toc = 'MORTGAGE PACKAGE - TABLE OF CONTENTS\\n';
            toc += '=' * 50 + '\\n\\n';
            toc += 'Generated: ' + new Date().toLocaleString() + '\\n';
            toc += 'Processing: Local Server (Private)\\n\\n';
            
            selectedSections.forEach((section, index) => {
                const pageStr = `Page ${section.page}`.padStart(10);
                toc += `${(index + 1).toString().padStart(2)}. ${section.section_type.padEnd(40, '.')} ${pageStr}\\n`;
            });

            toc += '\\n' + '=' * 50 + '\\n';
            toc += `Total Sections: ${selectedSections.length}\\n`;

            // Create downloadable file
            const blob = new Blob([toc], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mortgage_package_toc.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showSuccess(`Table of Contents generated and downloaded! (${selectedSections.length} sections)`);
        }

        function showError(message) {
            console.error('❌ Error:', message);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            document.querySelector('.container').appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 8000);
        }

        function showSuccess(message) {
            console.log('✅ Success:', message);
            const successDiv = document.createElement('div');
            successDiv.className = 'success';
            successDiv.textContent = message;
            document.querySelector('.container').appendChild(successDiv);
            setTimeout(() => successDiv.remove(), 5000);
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("=" * 60)
    print("🏠 MORTGAGE PACKAGE ANALYZER - LOCAL SERVER")
    print("=" * 60)
    print(f"📍 Server starting at: http://localhost:5000")
    print(f"🔒 Privacy: All processing happens locally")
    print(f"📊 OCR Available: {OCR_AVAILABLE}")
    print(f"📄 PDF Processing: {PDFPLUMBER_AVAILABLE}")
    print("=" * 60)
    print("💡 To stop the server, press Ctrl+C")
    print("=" * 60)
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

