import os
import fitz
from google import genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Anti-IT Audit API")

# Root route for Render health checks
@app.get("/")
async def root():
    return {"status": "active", "service": "Anti-IT Audit"}

# Initialize the 2026 SDK Client
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Critical Error: GEMINI_API_KEY is missing")

client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = """
Role: You are a Senior CTO and independent audit expert. 
Objective: Perform a brutal Sanity Check of the IT estimate. 
Output: Strictly JSON. 
Focus on over-engineering, hourly padding, and technology relevance.
"""

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("No context provided")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files accepted.")

    try:
        # Extract text from PDF
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        proposal_text = "".join(page.get_text() for page in doc)
        
        if len(proposal_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="PDF is empty or non-readable.")

        # Modern SDK syntax
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{business_context}\n\nESTIMATE TEXT:\n{proposal_text}"
        )
        
        return JSONResponse(content={"status": "success", "audit": response.text})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Audit failed", "details": str(e)})
