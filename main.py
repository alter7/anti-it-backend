import os
import fitz  # PyMuPDF
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Anti-IT Audit API")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Critical Error: GEMINI_API_KEY is not set")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """
Role: You are a Senior CTO and an independent IT audit expert. Your specialization is detecting fraud, padded estimates, and over-engineering in software development proposals.
Objective: Perform a brutal Sanity Check of the provided estimate against the client's business context.
Output Format (JSON strictly):
{
  "overall_verdict": "Red/Yellow/Green",
  "overcharge_estimate": "Estimated overcharged amount in USD",
  "top_red_flags": ["flag 1", "flag 2", "flag 3"],
  "cost_savings": "Potential cost savings",
  "awkward_questions": ["question 1", "question 2", "question 3"]
}
Tone: Brutally honest, cynical, business-oriented. You are on the client's side.
"""

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF reading error: {str(e)}")

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("No context provided")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    proposal_text = extract_text_from_pdf(file_bytes)

    if len(proposal_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="PDF is empty or contains only images (scan).")

    prompt = f"""
    {SYSTEM_PROMPT}
    
    === CLIENT BUSINESS CONTEXT ===
    {business_context}
    
    === PROPOSAL TEXT ===
    {proposal_text}
    """

    try:
        response = model.generate_content(prompt)
        return JSONResponse(content={"status": "success", "raw_audit": response.text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(e)}")
