# agents/calendar_agent.py
print(">>> Loaded calendar_agent_streamlit.py from:", __file__)
import datetime
import os
import pickle
import pytz
import streamlit as st
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_PATH = 'token.pkl'
CREDENTIALS_PATH = 'credentials.json'


def authenticate_google():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token_file:
            pickle.dump(creds, token_file)
    return creds


def create_calendar_event(creds, summary, start_dt, end_dt, description='', attendees=None, timezone='Africa/Lagos'):
    attendees = attendees or []
    service = build('calendar', 'v3', credentials=creds)
    event_body = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': timezone},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': timezone},
        'attendees': [{'email': email} for email in attendees],
        'reminders': {'useDefault': True},
    }
    event = service.events().insert(calendarId='primary', body=event_body, sendUpdates='all').execute()
    st.success(f"Event created: [Link]({event.get('htmlLink')})")


def list_today_calendar_events_streamlit(creds):
    service = build('calendar', 'v3', credentials=creds)
    local_tz = pytz.timezone('Africa/Lagos')
    now = datetime.datetime.now(local_tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    if not events:
        st.info("🌸 No events scheduled for today.")
        return

    for event in events:
        summary = event.get('summary', 'No Title')
        if 'dateTime' in event['start']:
            start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            st.write(f"🕒 {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} | {summary}")
        else:
            st.write(f"📅 All Day | {summary}")


def calendar_agent_menu_streamlit():
    st.subheader("📅 Calendar Agent")
    creds = authenticate_google()
    local_tz = pytz.timezone('Africa/Lagos')

    option = st.selectbox("Choose an action", ["View Today's Events", "Create New Event"])

    if option == "View Today's Events":
        list_today_calendar_events_streamlit(creds)

    elif option == "Create New Event":
        summary = st.text_input("Event Title")
        description = st.text_area("Description (optional)")
        attendees = st.text_input("Attendees' emails, comma separated")
        date_input = st.date_input("Event Date")
        start_time_input = st.time_input("Start Time")
        end_time_input = st.time_input("End Time")

        if st.button("Create Event"):
            start_dt = local_tz.localize(datetime.datetime.combine(date_input, start_time_input))
            end_dt = local_tz.localize(datetime.datetime.combine(date_input, end_time_input))
            attendees_list = [email.strip() for email in attendees.split(",") if email.strip()]
            create_calendar_event(creds, summary, start_dt, end_dt, description, attendees_list)


