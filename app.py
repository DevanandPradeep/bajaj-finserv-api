from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Union, Dict, Any
import uvicorn
import json
from bajaj_pipeline.main import process_request

app = FastAPI(
    title="Bajaj Finserv Document Extraction API",
    description="API for extracting line items from medical bills"
)

class DocumentRequest(BaseModel):
    document: str

@app.post("/extract-bill-data")
async def extract_bill_data(request: DocumentRequest):
    """
    Extract line items from a bill document.
    
    The document can be a URL or a local file path.
    """
    try:
        # Convert Pydantic model to list of dicts as expected by process_request
        payload = [request.model_dump()]
        
        # Process the document
        result = process_request(payload)
        
        # result[1] contains the actual response data
        response_data = result[1] if len(result) > 1 else result[0]
        
        # Add page_type to each page (we'll need to enhance this with actual classification)
        if "data" in response_data and "pagewise_line_items" in response_data["data"]:
            for page in response_data["data"]["pagewise_line_items"]:
                # Default to "Bill Detail" for now - this can be enhanced with ML classification
                page["page_type"] = "Bill Detail"
        
        # Add token_usage (currently 0 as we're not using LLM)
        # This will be updated when LLM integration is added
        response_data["token_usage"] = {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }
        
        return response_data
        
    except Exception as e:
        return {
            "is_success": False,
            "token_usage": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0
            },
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
