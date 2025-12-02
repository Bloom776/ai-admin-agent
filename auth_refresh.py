from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

def authenticate_google():
    creds = None
    token_path = 'token.json'
    if os.path.exists(token_path):
        try:
            # Try loading existing credentials
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            creds.refresh(Request())
            print("✅ Token refreshed successfully")
            return creds
        except Exception as e:
            print("⚠️ Refresh failed, reauthenticating:", e)

    # Force reauthentication
    print("🌐 Opening browser for manual login...")
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_path, 'w') as token:
        token.write(creds.to_json())
    print("✅ New token saved.")
    return creds

if __name__ == "__main__":
    authenticate_google()