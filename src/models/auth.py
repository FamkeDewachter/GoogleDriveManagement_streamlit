import streamlit as st
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token file.
SCOPES = [
    # Full access to Google Drive (read/write)
    "https://www.googleapis.com/auth/drive",
    # Access to files created or opened by the app
    "https://www.googleapis.com/auth/drive.file",
    # For user profile
    "https://www.googleapis.com/auth/userinfo.profile",
    # For user email
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def authenticate_google_drive_web():
    """
    Authenticates via Google OAuth and returns:
    - drive_service
    - user_name
    - user_email
    All credentials are stored in st.session_state
    """
    # Initialize session state
    if "google_auth" not in st.session_state:
        st.session_state.google_auth = {
            "creds": None,
            "user_name": None,
            "user_email": None,
        }
    # Return cached credentials if valid
    if (
        st.session_state.google_auth["creds"]
        and st.session_state.google_auth["creds"].valid
    ):
        try:
            drive_service = build(
                "drive",
                "v3",
                credentials=st.session_state.google_auth["creds"],
            )
            return (
                drive_service,
                st.session_state.google_auth["user_name"],
                st.session_state.google_auth["user_email"],
            )
        except HttpError as e:
            st.error(f"Google API error: {e}")
            return None, None, None

    # OAuth Flow
    try:
        flow = InstalledAppFlow.from_client_config(
            client_config=st.secrets["google"], scopes=SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Get user profile
        people_service = build("people", "v1", credentials=creds)
        profile = (
            people_service.people()
            .get(resourceName="people/me", personFields="names,emailAddresses")
            .execute()
        )

        # Extract user info
        user_name = profile.get("names", [{}])[0].get("displayName", "Unknown")
        user_email = profile.get("emailAddresses", [{}])[0].get(
            "value", "unknown"
        )

        # Store in session state
        st.session_state.google_auth = {
            "creds": creds,
            "user_name": user_name,
            "user_email": user_email,
        }

        drive_service = build("drive", "v3", credentials=creds)
        return drive_service, user_name, user_email

    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None, None, None
