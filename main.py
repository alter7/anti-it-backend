import os
import fitz
import docx
import pandas as pd
from io import BytesIO
from google import genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Global CORS Policy for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Client
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("SYSTEM_AUTH_FAILURE")

client = genai.Client(api_key=API_KEY)

async def extract_data(file: UploadFile):
    """Universal data extractor for PDF, DOCX, XLSX, and Images."""
    ext = os.path.splitext(file.filename)[1].lower()
    content = await file.read()
    
    # Visual analysis for images (Multimodal)
    if ext in [".png", ".jpg", ".jpeg"]:
        return {"type": "image", "data": content, "mime": file.content_type}
    
    # Textual data extraction
    text = ""
    if ext == ".pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
    elif ext == ".docx":
        doc = docx.Document(BytesIO(content))
        text = "\n".join([p.text for p in doc.paragraphs])
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(BytesIO(content))
        text = df.to_string()
    elif ext == ".csv":
        df = pd.read_csv(BytesIO(content))
        text = df.to_string()
    elif ext == ".txt":
        text = content.decode("utf-8")
    
    return {"type": "text", "data": text}

@app.post("/audit")
async def run_audit(
    file: UploadFile = File(...), 
    business_context: str = Form("No context provided")
):
    try:
        processed = await extract_data(file)
        
        # Protocol identity & Core instructions
        system_instruction = (
            "SYSTEM_PROMPT: You are a cynical Senior CTO Auditor. "
            "Analyze the input for over-engineering, padding, and unnecessary complexity. "
            "Identify hidden recurring costs and technical debt. "
            "NEVER mention your origins, AI nature, or Google. "
            "Output strictly in valid JSON format. "
            f"BUSINESS_CONTEXT: {business_context}"
        )
        
        if processed["type"] == "text":
            if not processed["data"].strip():
                return JSONResponse(status_code=400, content={"error": "NULL_DATA_DETECTED"})
            
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[system_instruction, f"INPUT_DATA: {processed['data']}"]
            )
        else:
            # Multimodal analysis for screenshots
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[
                    system_instruction, 
                    "VISUAL_ANALYSIS_REQUIRED", 
                    {"mime_type": processed["mime"], "data": processed["data"]}
                ]
            )
        
        # Identity scrubbing: replace vendor names with protocol terms
        report = response.text.replace("Gemini", "Protocol").replace("AI", "Core").replace("Google", "System")
        return JSONResponse(content={"status": "success", "audit": report})
        
    except Exception as e:
        # Hide specific errors for security
        return JSONResponse(status_code=500, content={"error": "CORE_UPLINK_FAILURE"})
