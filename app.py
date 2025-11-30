from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Dict, Any
import uvicorn
import json
import logging
import time
import sys
from bajaj_pipeline.main import process_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bajaj-api")

app = FastAPI(
    title="Bajaj Finserv Document Extraction API",
    description="API for extracting line items from medical bills"
)

# Add CORS middleware to allow requests from any origin (e.g., verify.html)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class DocumentRequest(BaseModel):
    document: str

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Request completed: {response.status_code} in {process_time:.2f}ms")
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"Request failed: {str(e)} in {process_time:.2f}ms", exc_info=True)
        raise e

@app.post("/extract-bill-data")
async def extract_bill_data(request: DocumentRequest):
    """
    Extract line items from a bill document.
    
    The document can be a URL or a local file path.
    """
    logger.info(f"Processing extraction request for document: {request.document}")
    try:
        # Convert Pydantic model to list of dicts as expected by process_request
        payload = [request.model_dump()]
        
        # Process the document
        start_process = time.time()
        result = process_request(payload)
        logger.info(f"Core processing took {(time.time() - start_process):.2f}s")
        
        # result[1] contains the actual response data
        response_data = result[1] if len(result) > 1 else result[0]
        
        # Add page_type to each page (we'll need to enhance this with actual classification)
        if "data" in response_data and "pagewise_line_items" in response_data["data"]:
            for page in response_data["data"]["pagewise_line_items"]:
                # Default to "Bill Detail" for now - this can be enhanced with ML classification
                page["page_type"] = "Bill Detail"
        
        logger.info("Extraction successful")
        return response_data
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)
        return {
            "is_success": False,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {
        "message": "Bajaj Finserv Extraction API is running",
        "endpoints": {
            "extract": "POST /extract-bill-data"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
