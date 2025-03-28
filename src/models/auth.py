import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from urllib.parse import urlparse, parse_qs

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
        return "https://gdrive-management.streamlit.app/"
    return "http://localhost:8501/"


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
        redirect_uri = get_redirect_uri()
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": st.secrets["google"]["client_id"],
                    "client_secret": st.secrets["google"]["client_secret"],
                    "auth_uri": st.secrets["google"]["auth_uri"],
                    "token_uri": st.secrets["google"]["token_uri"],
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        # Check for authorization code in query params
        query_params = st.experimental_get_query_params()
        if "code" in query_params:
            code = query_params["code"][0]
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
            st.experimental_set_query_params()  # Clear the code from URL
            st.rerun()

        # If not authenticated, show login button
        if not st.session_state.google_auth["creds"]:
            auth_url, _ = flow.authorization_url(prompt="consent")
            if st.button("Login with Google"):
                st.write(f"Please [click here to authenticate]({auth_url})")
                # Or use JavaScript redirect
                # st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                return None, None, None
        st.write(f"Redirect URI: {redirect_uri}")
        st.write(f"Query params: {st.experimental_get_query_params()}")

        # If we have credentials, return them
        if st.session_state.google_auth["creds"]:
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

        return None, None, None

    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None, None, None
