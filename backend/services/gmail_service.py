# backend/services/gmail_service.py (FINAL - Clean Slate)
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

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

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
    is_pdf = "pdf" in mime_type.lower() or (filename and filename.lower().endswith('.pdf'))
    if not is_pdf:
        return f"CRITICAL ERROR: File '{filename}' was not identified as a PDF (MIME type: '{mime_type}')."

    text_content = ""
    try:
        try:
            reader = PdfReader(io.BytesIO(file_data))
            for page in reader.pages:
                text_content += page.extract_text() or ""
        except Exception:
            text_content = ""

        if len(text_content.strip()) < 100:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file_data)
                temp_pdf_path = temp_pdf.name
            try:
                pages = convert_from_path(temp_pdf_path, 300)
                ocr_text = ""
                for page_image in pages:
                    ocr_text += pytesseract.image_to_string(page_image, lang='eng') + "\n"
                if len(ocr_text.strip()) > len(text_content.strip()):
                    text_content = ocr_text
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)

        if not text_content.strip():
             return "Could not extract readable text. The PDF may be an image or encrypted."
        return text_content.strip()
    except Exception as e:
        print(f"CRITICAL ERROR during PDF parsing for '{filename}': {e}")
        return f"A critical error occurred while processing the PDF: {type(e).__name__}."

async def get_attachment_text(service, message_id: str, attachment_id: str, filename: str, mime_type: str):
    try:
        attachment_meta = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id).execute()
        data = attachment_meta.get('data')
        if not data: raise ValueError("Attachment data not found in API response.")
        file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
        return extract_text_from_attachment(mime_type, file_data, filename)
    except Exception as e:
        print(f'CRITICAL ERROR in get_attachment_text: {e}')
        return f"A critical error occurred: {type(e).__name__} - {e}"

def get_all_parts(payload):
    parts_to_process = [payload]; flat_parts_list = []
    while parts_to_process:
        current_part = parts_to_process.pop(0)
        flat_parts_list.append(current_part)
        if 'parts' in current_part: parts_to_process.extend(current_part['parts'])
    return flat_parts_list

def get_email_body(parts):
    body_html = None; body_plain = None
    def recurse_parts(sub_parts):
        nonlocal body_html, body_plain
        for part in sub_parts:
            if part.get('body', {}).get('data'):
                mime_type = part.get('mimeType', ''); data = part['body']['data']
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                if mime_type == 'text/html': body_html = decoded_data
                elif mime_type == 'text/plain': body_plain = decoded_data
            if part.get('parts'): recurse_parts(part['parts'])
    recurse_parts(parts)
    return body_html, body_plain

async def fetch_emails(service, max_results=20):
    try:
        results = service.users().messages().list(userId='me', maxResults=max_results, q="in:inbox").execute()
        messages = results.get('messages', []);
        if not messages: return []
        email_list = []
        def process_response(request_id, response, exception):
            if not exception and response:
                headers = response.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                email_list.append({
                    'id': response['id'], 'threadId': response['threadId'], 'subject': subject,
                    'sender': sender, 'snippet': response['snippet']
                })
        batch = service.new_batch_http_request(callback=process_response)
        for message in messages:
            batch.add(service.users().messages().get(userId='me', id=message['id']))
        batch.execute()
        return email_list
    except HttpError as error:
        print(f'An error occurred fetching emails: {error}'); raise

async def fetch_single_email(service, message_id: str):
    try:
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = msg.get('payload', {}); headers = payload.get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        body_html, body_plain = None, "No text content found."; attachments = []
        all_parts = get_all_parts(payload)
        for part in all_parts:
            if 'attachmentId' in part.get('body', {}):
                filename = part.get('filename')
                if not filename:
                    for header in part.get('headers', []):
                        if header.get('name', '').lower() == 'content-disposition':
                            for part_str in header.get('value', '').split(';'):
                                if part_str.strip().lower().startswith('filename='):
                                    filename = part_str.split('=', 1)[1].strip().replace('"', '')
                                    break
                attachments.append({'id': part['body']['attachmentId'], 'filename': filename, 'mimeType': part.get('mimeType')})
        if 'parts' in payload: body_html, body_plain = get_email_body(payload['parts'])
        elif payload.get('body', {}).get('data'):
            decoded_body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
            if payload.get('mimeType') == 'text/html': body_html = decoded_body
            else: body_plain = decoded_body
        return {'id': msg['id'], 'subject': subject, 'sender': sender, 'snippet': msg['snippet'], 'body': body_html or body_plain, 'attachments': attachments}
    except HttpError as error: print(f'An error fetching single email: {error}'); raise

async def send_email(service, to: str, subject: str, body: str):
    try:
        message = MIMEText(body); message['to'] = to; message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        return service.users().messages().send(userId='me', body=create_message).execute()
    except HttpError as error: print(f'An error sending email: {error}'); raise