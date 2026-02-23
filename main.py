import os
import fitz
import docx
import pandas as pd
import json
from io import BytesIO
from google import genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

async def extract_data(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    content = await file.read()
    if ext in [".png", ".jpg", ".jpeg"]:
        return {"type": "image", "data": content, "mime": file.content_type}
    
    text = ""
    if ext == ".pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
    elif ext == ".docx":
        doc = docx.Document(BytesIO(content))
        text = "\n".join([p.text for p in doc.paragraphs])
    elif ext in [".xlsx", ".xls"]:
        text = pd.read_excel(BytesIO(content)).to_string()
    elif ext in [".csv", ".txt"]:
        text = content.decode("utf-8")
    
    return {"type": "text", "data": text}

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("Not provided"),
    client_location: str = Form("Global")
):
    try:
        processed = await extract_data(file)
        
        system_instructions = """ROLE: Synthetic CTO Forensic Auditor v4.2. You represent the CLIENT.
OBJECTIVE: Cold, cynical truth, objective risk assessment, and financial efficiency.
TASK: Audit the provided 'VENDOR_PROPOSAL' against 'CLIENT_CONTEXT' and 'CLIENT_LOCATION'.

STRICT CONSTRAINTS:
1. Tone: Brutally honest, highly technical, direct. No sugar-coating.
2. If the solution is over-engineered, state the exact risk.
3. Factor in the 'CLIENT_LOCATION' to evaluate if pricing is a scam relative to regional 2026 market rates.
4. Output MUST be strictly valid JSON only. Do not wrap in ```json block.

JSON STRUCTURE TO POPULATE:
{
  "executive_verdict": "1-2 sentences. Brutal summary of the proposal's fairness.",
  "top_red_flag": "The single most critical scam, padding, or risk found.",
  "risk_radar": [0,0,0,0,0], 
  "line_by_line_audit": ["Point 1", "Point 2"], 
  "stack_sanity_check": "Analyze if the tech stack is overkill for the context.",
  "alternative_solutions": "Name specific SaaS, No-Code, or cheaper architectural paths.",
  "ideal_contractor": "Profile the exact type of vendor needed (grade, region, rate).",
  "negotiation_script": ["Question 1", "Question 2"]
}"""
        
        prompt_content = [
            system_instructions, 
            f"CLIENT_CONTEXT: {business_context}",
            f"CLIENT_LOCATION: {client_location}"
        ]
        
        if processed["type"] == "text":
            prompt_content.append(f"VENDOR_PROPOSAL: {processed['data']}")
        else:
            prompt_content.append({"mime_type": processed["mime"], "data": processed["data"]})

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_content
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        audit_data = json.loads(clean_text)
        
        return JSONResponse(content={"status": "success", "audit": audit_data})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "PROTOCOL_UPLINK_ERROR", "details": str(e)})
