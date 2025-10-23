# backend/main.py (FINAL - With Calendar Feature)
import os
import json
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bs4 import BeautifulSoup

from database import create_db_and_tables, get_session
from models import User
from auth import oauth, create_access_token, find_or_create_user, get_current_user
# --- THIS IS THE FIRST CHANGE: Import the new calendar service ---
from services import gmail_service, ai_service, calendar_service

load_dotenv()
CLIENT_URL = os.getenv("CLIENT_URL")
SESSION_SECRET_KEY = os.getenv("JWT_SECRET")
if not CLIENT_URL or not SESSION_SECRET_KEY:
    raise ValueError("CLIENT_URL and JWT_SECRET must be set in .env file!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO:     Starting up and creating database tables...")
    await create_db_and_tables()
    print("INFO:     Startup complete.")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=[CLIENT_URL], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# --- Pydantic Models ---
class AttachmentInfo(BaseModel):
    id: str; filename: str; mimeType: str

class EmailSchema(BaseModel):
    to: EmailStr; subject: str; body: str

class SummarizeRequest(BaseModel):
    text: str

class GenerateReplyRequest(BaseModel):
    prompt: str
    
# --- THIS IS THE SECOND CHANGE: Add the new Calendar model ---
class CalendarEventRequest(BaseModel):
    title: str
    date_string: str
    context: str

# --- API Routes ---
@app.get("/auth/google")
async def login(request: Request):
    assert oauth.google is not None
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback", name="auth_callback")
async def auth_callback(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        assert oauth.google is not None
        token = await oauth.google.authorize_access_token(request)
        user_info = token['userinfo']
        db_user = await find_or_create_user(session, user_info, token)
        access_token = create_access_token(data={"sub": str(db_user.id)})
        return RedirectResponse(url=f"{CLIENT_URL}/dashboard?token={access_token}")
    except Exception as e:
        print(f"ERROR during auth callback: {e}")
        return RedirectResponse(url=f"{CLIENT_URL}/login/error")

@app.get("/api/me", response_model=User)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/gmail/inbox")
async def get_inbox(current_user: User = Depends(get_current_user)):
    service = gmail_service.get_gmail_service(current_user)
    emails = await gmail_service.fetch_emails(service)
    return {"emails": emails}

@app.get("/api/gmail/email/{message_id}")
async def get_email_content(message_id: str, current_user: User = Depends(get_current_user)):
    service = gmail_service.get_gmail_service(current_user)
    email_content = await gmail_service.fetch_single_email(service, message_id)
    return email_content

@app.post("/api/gmail/email/{message_id}/summarize-attachment")
async def summarize_attachment_api(message_id: str, attachment: AttachmentInfo, current_user: User = Depends(get_current_user)):
    service = gmail_service.get_gmail_service(current_user)
    text = await gmail_service.get_attachment_text(
        service, message_id=message_id, attachment_id=attachment.id,
        filename=attachment.filename, mime_type=attachment.mimeType
    )
    if "error" in text.lower() or "could not" in text.lower():
        return {"summary": text}
    summary = await ai_service.summarize_text(text)
    return {"summary": summary}

@app.post("/api/gmail/send")
async def send_new_email(email_data: EmailSchema, current_user: User = Depends(get_current_user)):
    service = gmail_service.get_gmail_service(current_user)
    sent_email = await gmail_service.send_email(service, to=email_data.to, subject=email_data.subject, body=email_data.body)
    return {"message": "Email sent successfully!", "details": sent_email}

@app.post("/api/ai/summarize")
async def api_summarize_text(request: SummarizeRequest, current_user: User = Depends(get_current_user)):
    if not request.text or not request.text.strip():
        return {"summary": "Error: Cannot summarize an empty email."}
    soup = BeautifulSoup(request.text, 'lxml')
    clean_text = soup.get_text(separator='\n', strip=True)
    if not clean_text:
        return {"summary": "Error: This email contains no readable text to summarize."}
    summary = await ai_service.summarize_text(clean_text)
    return {"summary": summary}

@app.post("/api/ai/generate-reply")
async def api_generate_reply(request: GenerateReplyRequest, current_user: User = Depends(get_current_user)):
    reply = await ai_service.generate_reply(request.prompt)
    return {"reply": reply}

# --- THIS IS THE THIRD CHANGE: The new Calendar endpoint ---
@app.post("/api/calendar/create-event")
async def create_event_api(
    event_request: CalendarEventRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Uses AI to parse a date string and creates a Google Calendar event.
    """
    if not ai_service.model:
        raise HTTPException(status_code=503, detail="AI Service is not initialized.")

    prompt = f"""
    Given the current date of {datetime.utcnow().strftime('%Y-%m-%d')}, parse the following text string into a structured date and time.
    The user wants to create a one-hour calendar event based on this.

    Text to parse: "{event_request.date_string}"
    Context from email: "{event_request.context}"
    
    Your response MUST be ONLY a single, raw JSON object with this exact structure:
    {{
        "start_iso": "YYYY-MM-DDTHH:MM:SSZ",
        "end_iso": "YYYY-MM-DDTHH:MM:SSZ"
    }}
    
    - Assume a default time of 9:00 AM if no time is specified.
    - The end time should be exactly one hour after the start time.
    - The format must be a valid ISO 8601 string in UTC (e.g., 2025-10-25T09:00:00Z).
    """
    
    try:
        response = await ai_service.model.generate_content_async(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        parsed_times = json.loads(raw_text)
        start_time = parsed_times['start_iso']
        end_time = parsed_times['end_iso']
    except Exception as e:
        print(f"ERROR parsing date with AI: {e}")
        raise HTTPException(status_code=500, detail="AI failed to parse the date string.")

    service = calendar_service.get_calendar_service(current_user)
    result = await calendar_service.create_calendar_event(
        service,
        title=event_request.title,
        start_time=start_time,
        end_time=end_time,
        description=f"Created by bharath.ai from an email with the subject: '{event_request.title}'"
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
        
    return result

@app.get("/")
async def read_root():
    return {"message": "bharath.ai Backend is running!"}