# doc_agent.py
from googleapiclient.discovery import build
from utils.google_auth import get_google_creds
import openai
import os

# Load API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

# === Transcript Fetcher ===
def get_transcript(provider="manual", transcript_text=None, **kwargs):
    if provider == "manual":
        return transcript_text or ""
    elif provider == "otter":
        return "Simulated Otter transcript: Replace with real API call."
    elif provider == "zoom":
        return "Simulated Zoom transcript: Replace with real API call."
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# === Google Docs Utilities ===
def create_doc_with_content(title, content):
    creds = get_google_creds(SCOPES)
    service = build('docs', 'v1', credentials=creds)

    doc = service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']

    requests_payload = [{
        'insertText': {
            'location': {'index': 1},
            'text': content
        }
    }]
    service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests_payload}
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"

def generate_pre_call_brief(title, attendees, agenda, bios=None, threads=None, notes=None):
    content = f"""
📄 **Pre-Call Brief: {title}**

👥 **Attendees**: {', '.join(attendees)}
🗓️ **Agenda**:
{agenda}

🧠 **Attendee Bios**:
{bios or 'To be filled'}

📩 **Recent Email Threads**:
{threads or 'No threads found.'}

📝 **Past Notes**:
{notes or 'No prior meeting notes found.'}
"""
    return create_doc_with_content(f"{title} - Pre-Call Brief", content.strip())

def summarize_meeting(transcript_text):
    prompt = f"""
Summarize this meeting transcript.

Transcript:
\"\"\"{transcript_text}\"\"\"
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content

def draft_follow_up_email(contact_name, summary, action_items):
    prompt = f"""
Write a friendly, professional follow-up email to {contact_name}.

Summary:
{summary}

Action items:
{action_items}
"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

def extract_tasks_from_summary(summary):
    prompt = f"Extract actionable tasks from: {summary}"
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

def fetch_latest_meeting_notes(keyword):
    creds = get_google_creds(SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    response = drive_service.files().list(
        q=f"mimeType='application/vnd.google-apps.document' and name contains '{keyword}'",
        orderBy='modifiedTime desc',
        pageSize=1,
        fields='files(id, name)'
    ).execute()

    files = response.get('files', [])
    if not files:
        return "No matching past notes found."

    doc_id = files[0]['id']
    doc = docs_service.documents().get(documentId=doc_id).execute()

    content = ""
    for element in doc.get('body', {}).get('content', []):
        text_run = element.get('paragraph', {}).get('elements', [{}])[0].get('textRun')
        if text_run:
            content += text_run.get('content', '')

    return content[:1500] + ("..." if len(content) > 1500 else "")
