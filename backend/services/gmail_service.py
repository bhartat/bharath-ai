# backend/services/gmail_service.py (FINAL - Definitive with Thread Feature)
import base64, os, io, tempfile
from email.mime.text import MIMEText
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from pypdf import PdfReader
import pandas as pd
import docx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import User
from bs4 import BeautifulSoup

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/calendar.events']

def get_gmail_service(user: User):
    if not user.oauth_access_token: raise ValueError("User has not granted Gmail permissions.")
    creds = Credentials(
        token=user.oauth_access_token, refresh_token=user.oauth_refresh_token,
        token_uri='https://oauth2.googleapis.com/token', client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"), scopes=SCOPES
    )
    try:
        return build('gmail', 'v1', credentials=creds, static_discovery=False)
    except HttpError as error:
        print(f'An error occurred building the Gmail service: {error}'); raise

def extract_text_from_attachment(mime_type: str, file_data: bytes, filename: str) -> str:
    # (This function is unchanged)
    is_pdf = "pdf" in mime_type.lower() or (filename and filename.lower().endswith('.pdf'))
    if not is_pdf: return f"CRITICAL ERROR: File '{filename}' not identified as PDF."
    text_content = ""
    try:
        try:
            reader = PdfReader(io.BytesIO(file_data))
            for page in reader.pages: text_content += page.extract_text() or ""
        except Exception: text_content = ""
        if len(text_content.strip()) < 100:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file_data)
                temp_pdf_path = temp_pdf.name
            try:
                pages = convert_from_path(temp_pdf_path, 300)
                ocr_text = ""
                for page_image in pages: ocr_text += pytesseract.image_to_string(page_image, lang='eng') + "\n"
                if len(ocr_text.strip()) > len(text_content.strip()): text_content = ocr_text
            finally:
                if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)
        if not text_content.strip(): return "Could not extract readable text from PDF."
        return text_content.strip()
    except Exception as e:
        print(f"CRITICAL ERROR during PDF parsing for '{filename}': {e}")
        return f"A critical error occurred while processing the PDF: {type(e).__name__}."

async def get_attachment_text(service, message_id: str, attachment_id: str, filename: str, mime_type: str):
    # (This function is unchanged)
    try:
        attachment_meta = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id).execute()
        data = attachment_meta.get('data')
        if not data: raise ValueError("Attachment data not found.")
        file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
        return extract_text_from_attachment(mime_type, file_data, filename)
    except Exception as e:
        print(f'CRITICAL ERROR in get_attachment_text: {e}')
        return f"A critical error occurred: {type(e).__name__} - {e}"

def get_all_parts(payload):
    # (This function is unchanged)
    parts = [payload]; flat_parts = []
    while parts:
        part = parts.pop(0)
        flat_parts.append(part)
        if 'parts' in part: parts.extend(part['parts'])
    return flat_parts

def get_email_body(parts):
    # (This function is unchanged)
    body_html, body_plain = None, None
    def recurse(sub_parts):
        nonlocal body_html, body_plain
        for part in sub_parts:
            if part.get('body', {}).get('data'):
                mime_type = part.get('mimeType', '')
                data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                if mime_type == 'text/html': body_html = data
                elif mime_type == 'text/plain': body_plain = data
            if part.get('parts'): recurse(part['parts'])
    recurse(parts)
    return body_html, body_plain

async def fetch_emails(service, max_results=20):
    # (This function is unchanged)
    try:
        results = service.users().messages().list(userId='me', maxResults=max_results, q="in:inbox").execute()
        messages = results.get('messages', []);
        if not messages: return []
        email_list = []
        def callback(req_id, resp, exc):
            if not exc and resp:
                headers = resp.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                email_list.append({'id': resp['id'], 'threadId': resp['threadId'], 'subject': subject, 'sender': sender, 'snippet': resp['snippet']})
        batch = service.new_batch_http_request(callback=callback)
        for msg in messages: batch.add(service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['subject', 'from']))
        batch.execute()
        return email_list
    except HttpError as error:
        print(f'An error occurred fetching emails: {error}'); raise

async def fetch_single_email(service, message_id: str):
    # (This function is unchanged)
    try:
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = msg.get('payload', {}); headers = payload.get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        body_html, body_plain = None, "No text"; attachments = []
        all_parts = get_all_parts(payload)
        for part in all_parts:
            if 'attachmentId' in part.get('body', {}):
                filename = part.get('filename')
                if not filename:
                    for header in part.get('headers', []):
                        if header.get('name', '').lower() == 'content-disposition':
                            for p_str in header.get('value', '').split(';'):
                                if p_str.strip().lower().startswith('filename='):
                                    filename = p_str.split('=', 1)[1].strip().replace('"', '')
                                    break
                attachments.append({'id': part['body']['attachmentId'], 'filename': filename, 'mimeType': part.get('mimeType')})
        if 'parts' in payload: body_html, body_plain = get_email_body(payload['parts'])
        elif payload.get('body', {}).get('data'):
            decoded = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
            if payload.get('mimeType') == 'text/html': body_html = decoded
            else: body_plain = decoded
        return {'id': msg['id'], 'threadId': msg['threadId'], 'subject': subject, 'sender': sender, 'snippet': msg['snippet'], 'body': body_html or body_plain, 'attachments': attachments}
    except HttpError as error: print(f'An error fetching single email: {error}'); raise

async def fetch_thread(service, thread_id: str) -> str:
    # (This function is unchanged)
    try:
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        combined_text = ""
        for message in thread.get('messages', []):
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
            body_html, body_plain = get_email_body([payload])
            clean_body = body_plain
            if not clean_body and body_html:
                clean_body = BeautifulSoup(body_html, 'lxml').get_text(separator='\n', strip=True)
            combined_text += f"--- Email from {sender} on {date} ---\n{clean_body}\n\n"
        return combined_text.strip()
    except HttpError as error:
        print(f'An error occurred fetching thread: {error}')
        return f"Error: Could not fetch thread. Details: {error}"

async def send_email(service, to: str, subject: str, body: str):
    # (This function is unchanged)
    try:
        message = MIMEText(body); message['to'] = to; message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        return service.users().messages().send(userId='me', body=create_message).execute()
    except HttpError as error: print(f'An error sending email: {error}'); raise