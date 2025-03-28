import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from urllib.parse import urlparse

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def get_redirect_uri():
    """Determine the correct redirect URI based on environment"""
    if os.getenv("IS_PRODUCTION", "false").lower() == "true":
        # Get the current URL in production
        current_url = st.experimental_get_query_params().get("url", [""])[0]
        if current_url:
            parsed = urlparse(current_url)
            return f"{parsed.scheme}://{parsed.netloc}/"
        return "https://gdrive-management.streamlit.app/"  # Fallback
    return st.secrets["google"]["redirect_uris"][0]  # Local development


def authenticate_google_drive_web():
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

    try:
        # Use the first redirect URI from secrets
        if not st.secrets["google.web"].get("redirect_uris"):
            st.error("Redirect URI configuration is missing in secrets")
            return None, None, None

        redirect_uri = st.secrets["google.web"]["redirect_uris"][0]

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": st.secrets["google.web"]["client_id"],
                    "client_secret": st.secrets["google.web"]["client_secret"],
                    "auth_uri": st.secrets["google.web"]["auth_uri"],
                    "token_uri": st.secrets["google.web"]["token_uri"],
                    "redirect_uris": st.secrets["google.web"]["redirect_uris"],
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        # Generate auth URL
        auth_url, _ = flow.authorization_url(prompt="consent")

        # Display login button
        if st.button("Login with Google"):
            st.session_state.auth_url = auth_url
            st.experimental_rerun()

        # Handle callback
        if "code" in st.experimental_get_query_params():
            code = st.experimental_get_query_params()["code"]
            flow.fetch_token(code=code)
            creds = flow.credentials

            # Get user profile
            people_service = build("people", "v1", credentials=creds)
            profile = (
                people_service.people()
                .get(
                    resourceName="people/me",
                    personFields="names,emailAddresses",
                )
                .execute()
            )

            # Extract user info
            user_name = profile.get("names", [{}])[0].get(
                "displayName", "Unknown"
            )
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

        return None, None, None

    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None, None, None
