# main_streamlit.py
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from controllers.main_controller import MainController
import toml
from pathlib import Path
import os
from urllib.parse import parse_qs, urlparse


def load_secrets():
    if st.secrets:
        return st.secrets
    else:
        try:
            return toml.load(Path(__file__).parent / "secrets.toml")
        except FileNotFoundError:
            return None


def get_redirect_uri():
    secrets = load_secrets()
    if not secrets:
        st.error("Failed to load authentication secrets")
        st.stop()

    uris = secrets["google"]["web"]["redirect_uris"]

    # If running in Streamlit Cloud
    if os.environ.get("STREAMLIT_SERVER_BASE_URL"):
        st.writeF("Running in Streamlit Cloud")
        return uris[1]  # Production URI

    # Default to localhost for development
    return uris[0]


def init_oauth_flow():
    secrets = load_secrets()
    if not secrets:
        st.error("Failed to load authentication secrets")
        st.stop()

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": secrets["google"]["web"]["client_id"],
                "client_secret": secrets["google"]["web"]["client_secret"],
                "auth_uri": secrets["google"]["web"]["auth_uri"],
                "token_uri": secrets["google"]["web"]["token_uri"],
                "redirect_uris": secrets["google"]["web"]["redirect_uris"],
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=get_redirect_uri(),
    )
    return flow


def get_authenticated_credentials():
    secrets = load_secrets()
    if not secrets:
        st.error("Failed to load authentication secrets")
        st.stop()

    flow = init_oauth_flow()

    # Get current URL
    current_url = (
        st.experimental_get_query_params()
        if hasattr(st, "experimental_get_query_params")
        else st.query_params.to_dict()
    )

    # Handle both string and list-type parameters
    if "code" in current_url:
        auth_code = current_url["code"]
        if isinstance(auth_code, list):
            auth_code = auth_code[0]

        try:
            # Exchange auth code for tokens
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            # Store credentials in session state
            st.session_state["credentials"] = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            }

            # Clear the code from URL
            if hasattr(st, "experimental_set_query_params"):
                st.experimental_set_query_params()
            else:
                st.query_params.clear()
            return credentials
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            st.session_state.pop("credentials", None)
            return None

    elif "credentials" in st.session_state:
        creds_data = st.session_state["credentials"]
        return Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )

    return None


def get_user_info(credentials):
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get("name", ""), user_info.get("email", "")
    except Exception as e:
        st.error(f"Error getting user info: {e}")
        return None, None


def authenticate():
    st.title("Google Drive Authentication")

    credentials = get_authenticated_credentials()

    if credentials:
        user_name, user_email = get_user_info(credentials)

        if user_name and user_email:
            st.session_state["user_name"] = user_name
            st.session_state["user_email"] = user_email

            drive_service = build("drive", "v3", credentials=credentials)
            return drive_service, user_name, user_email

    flow = init_oauth_flow()
    auth_url, _ = flow.authorization_url(prompt="consent")

    st.write(
        "Please sign in with your Google account to access the application."
    )
    st.markdown(
        f'<a href="{auth_url}" target="_self">Sign in with Google</a>',
        unsafe_allow_html=True,
    )

    st.stop()


def main():
    if "drive_service" not in st.session_state:
        drive_service, user_name, user_email = authenticate()
        st.session_state["drive_service"] = drive_service
        st.session_state["user_name"] = user_name
        st.session_state["user_email"] = user_email
    else:
        drive_service = st.session_state["drive_service"]
        user_name = st.session_state["user_name"]
        user_email = st.session_state["user_email"]

    app = MainController(drive_service, user_name, user_email)
    app.start()


if __name__ == "__main__":
    main()
