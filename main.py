import os
import fitz
import re
from google import genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("System Error: API_KEY_MISSING")

client = genai.Client(api_key=API_KEY)

def sanitize_output(text: str) -> str:
    """Removes any traces of AI vendor or regional language."""
    # Scrubbing English and Russian AI traces just in case
    forbidden = [
        "Gemini", "Google", "AI", "artificial intelligence", "language model", 
        "LLM", "ИИ", "интеллект", "модель", "джемини"
    ]
    for word in forbidden:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("Synthetic CTO Core", text)
    return text

@app.get("/")
async def health_check():
    return {"status": "operational", "engine": "Synthetic CTO Protocol v4.2"}

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("Context not provided")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="INVALID_FORMAT_PDF_ONLY")

    try:
        # Extract PDF content
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        proposal_text = "".join(page.get_text() for page in doc)
        
        if len(proposal_text.strip()) < 50:
            return JSONResponse(status_code=400, content={"error": "INSUFFICIENT_DATA_LENGTH"})

        # High-level audit request
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"SYSTEM: You are a cold, cynical Senior CTO Auditor. Perform a brutal forensic analysis. NEVER mention your origins or AI nature. Output strictly in valid JSON format. \nCONTEXT: {business_context} \nINPUT_DATA: {proposal_text}"
        )
        
        clean_report = sanitize_output(response.text)
        return JSONResponse(content={"status": "success", "audit": clean_report})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "code": "UPLINK_FAILURE"})
