# email_agent.py
import os
import re
import base64
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import openai

# ----------------------
# Configuration
# ----------------------
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]
CREDENTIALS_PATH = 'credentials.json'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY


# ----------------------
# Utilities
# ----------------------
def remove_hyperlinks(text):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\S+\.(com|net|org)\S*', '', text)
    return text


def chunk_text(text, max_chars):
    paragraphs = re.split(r'\n+', text)
    chunks, current_chunk = [], ''
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= max_chars:
            current_chunk += paragraph + '\n'
        else:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n'
    if current_chunk:
        chunks.append(current_chunk.strip())
    return [c for c in chunks if c.strip()]


def get_email_data(service, message_id):
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = message['payload']
    headers = payload.get('headers', [])
    email_data = {
        'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
        'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
        'date': next((h['value'] for h in headers if h['name'] == 'Date'), '')
    }

    data = None
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                data = part['body']['data']
                break
        if not data:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html' and part['body'].get('data'):
                    data = part['body']['data']
                    break
    else:
        data = payload.get('body', {}).get('data')

    if data:
        decoded = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8')
        soup = BeautifulSoup(decoded, 'html.parser')
        clean_text = remove_hyperlinks(soup.get_text())
        email_data['text'] = clean_text.strip()
    else:
        email_data['text'] = ''

    return email_data, message


def summarize_email(email_text, model="gpt-3.5-turbo"):
    system_prompt = (
        "You are a professional email summarizer. "
        "Create a short narrative paragraph then 2-4 bullet points. "
        "Keep under 120 words."
    )
    user_input = f"Summarize this email with a hybrid style: {email_text}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            top_p=1,
            presence_penalty=0.4,
            frequency_penalty=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Summary could not be generated due to an error."


def process_unread_emails(service, max_chars=3000, max_results=3):
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results
    ).execute()
    messages = results.get('messages', [])
    email_summaries = ""

    for message in messages:
        email_data, _ = get_email_data(service, message['id'])
        text = email_data.get('text', '').strip()
        if not text:
            continue

        chunks = chunk_text(text, max_chars)
        summary = ""
        for chunk in chunks:
            summary += summarize_email(chunk) + "\n"

        email_summaries += (
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Timestamp: {email_data['date']}\n"
            f"Link: https://mail.google.com/mail/u/0/#inbox/{message['id']}\n"
            f"Summary:\n{summary}\n\n"
        )

    return email_summaries


# ----------------------
# Streamlit Gmail OAuth
# ----------------------
def email_agent_menu():
    st.subheader("📧 Email Agent")
    st.write("Fetch and summarize your unread Gmail messages.")

    user_email = st.text_input("Enter your Gmail address:")
    if not user_email:
        st.info("Please enter your Gmail address to proceed.")
        return

    # OAuth flow
    creds = None
    if 'gmail_creds' not in st.session_state:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Streamlit-friendly
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.session_state.auth_url = auth_url
        st.write(f"[Click here to authenticate Gmail]({auth_url})")
        code = st.text_input("Enter the code from Gmail:")
        if code:
            flow.fetch_token(code=code)
            creds = flow.credentials
            st.session_state.gmail_creds = creds
        else:
            return
    else:
        creds = st.session_state.gmail_creds

    if st.button("Fetch Unread Emails"):
        service = build('gmail', 'v1', credentials=creds)
        summaries = process_unread_emails(service)
        if summaries.strip():
            st.text_area(f"📨 Email Summaries for {user_email}", summaries, height=300)
        else:
            st.info(f"🎉 No unread emails found for {user_email}!")
