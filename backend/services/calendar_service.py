# backend/services/calendar_service.py (NEW FILE)
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import User
from datetime import datetime, timedelta

def get_calendar_service(user: User):
    """Builds and returns an authenticated Google Calendar API service object."""
    creds = Credentials(
        token=user.oauth_access_token,
        refresh_token=user.oauth_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    try:
        service = build('calendar', 'v3', credentials=creds, static_discovery=False)
        return service
    except HttpError as error:
        print(f'An error occurred building the Calendar service: {error}')
        raise

async def create_calendar_event(service, title: str, start_time: str, end_time: str, description: str = ""):
    """Creates a new event on the user's primary calendar."""
    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC', # Standard practice to use UTC
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
    }
    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        return {"status": "success", "link": created_event.get('htmlLink')}
    except HttpError as error:
        print(f"An error occurred creating calendar event: {error}")
        return {"status": "error", "message": str(error)}