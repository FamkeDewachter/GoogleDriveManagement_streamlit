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
            error_details = f"""
            Google API error while using cached credentials:
            - Status: {e.status_code}
            - Reason: {e.error_details if hasattr(e, 'error_details') else 'No details'}
            - Message: {str(e)}
            """
            st.error(f"Google API error: {error_details}")
            return None, None, None

    try:
        # Check if Google secrets are properly configured
        if "google" not in st.secrets:
            st.error(
                "Google OAuth configuration is missing in Streamlit secrets."
            )
            return None, None, None

        if (
            "redirect_uris" not in st.secrets["google"]
            or not st.secrets["google"]["redirect_uris"]
        ):
            st.error("Redirect URI is missing in Google OAuth configuration.")
            return None, None, None

        flow = Flow.from_client_config(
            client_config=st.secrets["google"],
            scopes=SCOPES,
            redirect_uri=get_redirect_uri(),
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

            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
            except Exception as e:
                st.error(f"Failed to fetch access token: {str(e)}")
                return None, None, None

            try:
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

            except HttpError as e:
                error_details = f"""
                Google People API error:
                - Status: {e.status_code}
                - Reason: {e.error_details if hasattr(e, 'error_details') else 'No details'}
                - Message: {str(e)}
                """
                st.error(f"Failed to get user profile: {error_details}")
                return None, None, None

            except Exception as e:
                st.error(
                    f"Unexpected error while getting user profile: {str(e)}"
                )
                return None, None, None

        return None, None, None

    except Exception as e:
        error_type = type(e).__name__
        error_details = f"""
        Authentication failed:
        - Type: {error_type}
        - Message: {str(e)}
        """

        if hasattr(e, "args") and e.args:
            error_details += f"- Args: {e.args}\n"

        st.error(f"Authentication error: {error_details}")
        return None, None, None
