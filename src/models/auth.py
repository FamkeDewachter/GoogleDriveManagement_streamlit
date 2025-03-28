import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

CALLBACK_URL = "https://gdrive-management.streamlit.app/oauth-callback"


def get_auth_url():
    """Generate the authorization URL for initial redirect"""
    flow = Flow.from_client_config(
        client_config=st.secrets["google"],
        scopes=SCOPES,
        redirect_uri=CALLBACK_URL,
    )
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline"
    )
    st.session_state["oauth_flow"] = flow  # Store for callback phase
    return auth_url


def handle_oauth_callback():
    """Process the OAuth callback and return credentials"""
    if "oauth_flow" not in st.session_state:
        raise Exception("No OAuth flow in progress")

    flow = st.session_state["oauth_flow"]
    code = st.query_params().get("code")
    if not code:
        raise Exception("No authorization code found")

    # Exchange code for tokens
    creds = flow.fetch_token(code=code[0])

    # Get user info
    people_service = build("people", "v1", credentials=creds)
    profile = (
        people_service.people()
        .get(resourceName="people/me", personFields="names,emailAddresses")
        .execute()
    )

    return {
        "creds": creds,
        "user_name": profile.get("names", [{}])[0].get(
            "displayName", "Unknown"
        ),
        "user_email": profile.get("emailAddresses", [{}])[0].get(
            "value", "unknown"
        ),
    }


def check_existing_auth():
    """Check for valid existing credentials"""
    if "google_auth" not in st.session_state:
        return None

    creds = st.session_state.google_auth.get("creds")
    if creds and creds.valid:
        try:
            drive_service = build("drive", "v3", credentials=creds)
            return {
                "drive_service": drive_service,
                "user_name": st.session_state.google_auth["user_name"],
                "user_email": st.session_state.google_auth["user_email"],
            }
        except HttpError as e:
            st.error(f"Google API error: {e}")
    return None
