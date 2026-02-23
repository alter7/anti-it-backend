import os
import fitz
from google import genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Anti-IT Audit API")

# Root route for health checks
@app.get("/")
async def root():
    return {"status": "active", "service": "Anti-IT Audit"}

# Initialize Client
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=API_KEY)

def get_best_model():
    """Systematically finds the best available model for your key."""
    try:
        # Priority list for 2026
        preferred = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-002']
        available = [m.name.split('/')[-1] for m in client.models.list()]
        
        for model_id in preferred:
            if model_id in available:
                return model_id
        return available[0] if available else 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

MODEL_ID = get_best_model()

@app.get("/debug-models")
async def list_models():
    """Diagnostic endpoint to see what your API key can actually do."""
    try:
        models = [m.name for m in client.models.list()]
        return {"available_models": models, "selected_model": MODEL_ID}
    except Exception as e:
        return {"error": str(e)}

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("No context provided")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF accepted.")

    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        proposal_text = "".join(page.get_text() for page in doc)
        
        if len(proposal_text.strip()) < 50:
            return JSONResponse(status_code=400, content={"error": "PDF text too short"})

        # The actual AI call
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=f"Role: Senior CTO Audit Expert. Context: {business_context}. Analyze this estimate for over-engineering and padding. Output JSON. Estimate: {proposal_text}"
        )
        
        return JSONResponse(content={"status": "success", "audit": response.text})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Audit failed", "details": str(e), "model_used": MODEL_ID})
