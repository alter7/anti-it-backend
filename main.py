import os
import fitz  # PyMuPDF
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Anti-IT Audit API")

# Setup API Key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Critical Error: GEMINI_API_KEY is not set")

genai.configure(api_key=API_KEY)

# --- DIAGNOSTIC BLOCK ---
# This will print all available models to your Render logs on startup
print("--- DISCOVERING AVAILABLE MODELS ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Available model: {m.name}")
except Exception as e:
    print(f"Diagnostics failed: {e}")
# ------------------------

# Use the most stable production name
MODEL_NAME = 'gemini-1.5-flash' 
model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_PROMPT = """
Role: Senior CTO & Audit Expert. 
Objective: Brutal Sanity Check of the estimate.
Output: JSON only.
"""

@app.get("/health")
async def health_check():
    """Endpoint to verify the server is responding."""
    return {"status": "online", "model_configured": MODEL_NAME}

@app.post("/audit")
async def run_audit(file: UploadFile = File(...), business_context: str = Form("No context")):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF allowed.")
    
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        proposal_text = "".join(page.get_text() for page in doc)
        
        if len(proposal_text.strip()) < 50:
            return JSONResponse(status_code=400, content={"error": "PDF is too short or image-only"})

        response = model.generate_content(f"{SYSTEM_PROMPT}\nContext: {business_context}\nText: {proposal_text}")
        return JSONResponse(content={"status": "success", "audit": response.text})
    except Exception as e:
        # Return full error details for debugging
        return JSONResponse(status_code=500, content={"detail": str(e)})
