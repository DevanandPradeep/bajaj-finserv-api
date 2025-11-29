# Bajaj Finserv Medical Bill Extraction API

This project extracts line items from medical bills/invoices using OCR and layout-aware algorithms.

## Features

- **Multi-page PDF and Image Support**: Processes PDFs and images (PNG, JPG, etc.)
- **Layout-Aware Extraction**: Uses spatial analysis to identify tables and line items
- **Column Detection**: Automatically detects Quantity, Rate, and Amount columns
- **Spell Correction**: Corrects common OCR errors in medical terminology
- **RESTful API**: FastAPI-based endpoint for easy integration

## API Specification

### Endpoint
```
POST /extract-bill-data
```

### Request Format
```json
{
    "document": "https://example.com/bill.pdf"
}
```

The `document` field can be:
- A publicly accessible URL (http/https)
- A local file path (for development/testing)

### Response Format
```json
{
    "is_success": true,
    "token_usage": {
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0
    },
    "data": {
        "pagewise_line_items": [
            {
                "page_no": "1",
                "page_type": "Bill Detail",
                "bill_items": [
                    {
                        "item_name": "Consultation",
                        "item_amount": 500.0,
                        "item_rate": 500.0,
                        "item_quantity": 1.0
                    }
                ]
            }
        ],
        "total_item_count": 1,
        "reconciled_amount": 500.0
    }
}
```

## Installation

### Prerequisites
- Python 3.8+
- Tesseract OCR
- Poppler (for PDF processing)

### Windows
```bash
# Install Tesseract
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH

# Install Poppler
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Extract and add bin/ to PATH or set POPPLER_PATH environment variable
```

### Linux
```bash
sudo apt-get install tesseract-ocr poppler-utils
```

### Python Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Local Development
```bash
python -m uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`

### Testing
```bash
# Test with a local file
curl -X POST http://localhost:8000/extract-bill-data \
  -H "Content-Type: application/json" \
  -d '{"document": "Sample Document 1.pdf"}'

# Test with a URL
curl -X POST http://localhost:8000/extract-bill-data \
  -H "Content-Type: application/json" \
  -d '{"document": "https://example.com/bill.pdf"}'
```

## Deployment Options

### Option 1: Render (Recommended for Hackathons)
**Pros**: Free tier, easy setup, supports Python
**Cons**: Cold starts on free tier

1. Create a `render.yaml`:
```yaml
services:
  - type: web
    name: bajaj-extraction-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app:app --host 0.0.0.0 --port $PORT"
```

2. Push to GitHub
3. Connect to Render and deploy
4. Your webhook URL: `https://your-app.onrender.com/extract-bill-data`

### Option 2: Railway
**Pros**: Very easy setup, good free tier
**Cons**: Credit card required (even for free tier)

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Deploy: `railway up`
4. Your webhook URL: `https://your-app.railway.app/extract-bill-data`

### Option 3: Ngrok (Quick Testing)
**Pros**: Instant setup, no deployment needed
**Cons**: URL changes on restart, not for production

1. Download ngrok: https://ngrok.com/download
2. Run your API locally: `python -m uvicorn app:app`
3. In another terminal: `ngrok http 8000`
4. Your webhook URL: `https://xxxx.ngrok.io/extract-bill-data`

### Option 4: Google Cloud Run
**Pros**: Scales to zero, pay per use
**Cons**: Requires GCP account and credit card

1. Create `Dockerfile`
2. Deploy to Cloud Run
3. Your webhook URL: `https://your-service.run.app/extract-bill-data`

## Architecture

### Pipeline Flow
```
Document URL/Path
    ↓
Load & Convert to Images (preprocessing.py)
    ↓
OCR Processing (ocr_engines.py)
    ↓
Row Clustering & Header Detection (line_item_extractor.py)
    ↓
Column Assignment (Qty, Rate, Amount)
    ↓
Item Finalization & Validation
    ↓
JSON Response
```

### Key Components

1. **app.py**: FastAPI application and routing
2. **bajaj_pipeline/main.py**: Main processing orchestration
3. **bajaj_pipeline/preprocessing.py**: Document loading and image preprocessing
4. **bajaj_pipeline/ocr_engines.py**: OCR engine interfaces (Tesseract, DeepSight stub)
5. **bajaj_pipeline/line_item_extractor.py**: Layout-aware line item extraction

## Algorithm Details

### Line Item Extraction
1. **Image Preprocessing**: Grayscale, contrast enhancement, sharpening, binarization
2. **OCR**: Extract text boxes with coordinates
3. **Row Clustering**: Group boxes by vertical position
4. **Header Detection**: Identify column headers (Qty, Rate, Amount)
5. **Column Mapping**: Assign numeric values to appropriate columns
6. **Mathematical Validation**: Verify Qty × Rate = Amount
7. **Spell Correction**: Fix common OCR errors using fuzzy matching

## Limitations & Future Work

- **Current**: Only uses Tesseract OCR
- **Future**: Integrate DeepSight or other commercial OCR for better accuracy
- **Current**: Rule-based extraction
- **Future**: ML-based table detection and LLM-based extraction
- **Current**: Basic page type classification
- **Future**: Intelligent classification of Bill Detail vs Pharmacy vs Final Bill

## License
MIT

## Contact
For issues or questions, please open a GitHub issue.
