# auth.py
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

REDIRECT_URI = (
    "https://gdrive-management.streamlit.app/"  # Centralized for reuse
)


def initialize_auth_session():
    if "google_auth" not in st.session_state:
        st.session_state.google_auth = {
            "creds": None,
            "user_name": None,
            "user_email": None,
            "requested_scopes": None,
            "is_authenticated": False,
        }


def reset_auth_session():
    st.session_state.google_auth = {
        "creds": None,
        "user_name": None,
        "user_email": None,
        "requested_scopes": None,
        "is_authenticated": False,
    }
    st.rerun()


def get_google_flow():
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


def authenticate_user():
    initialize_auth_session()

    # Check existing credentials
    auth_data = st.session_state.google_auth
    creds = auth_data["creds"]

    if creds and creds.valid:
        if set(creds.scopes or []) == set(
            auth_data["requested_scopes"] or SCOPES
        ):
            auth_data["is_authenticated"] = True
            return True
        else:
            st.warning("Scope mismatch, resetting session.")
            reset_auth_session()
            return False

    flow = get_google_flow()
    st.session_state.google_auth["requested_scopes"] = SCOPES
    query_params = st.query_params.to_dict()

    # Handle OAuth callback
    if "code" in query_params:
        try:
            flow.fetch_token(code=query_params["code"])
            creds = flow.credentials

            # Extra check for scope mismatch
            if set(creds.scopes or []) != set(SCOPES):
                raise ValueError(
                    "Granted scopes do not match requested scopes."
                )

            # Fetch user info
            people_service = build("people", "v1", credentials=creds)
            profile = (
                people_service.people()
                .get(
                    resourceName="people/me",
                    personFields="names,emailAddresses",
                )
                .execute()
            )

            st.session_state.google_auth.update(
                {
                    "creds": creds,
                    "user_name": profile.get("names", [{}])[0].get(
                        "displayName", "Unknown"
                    ),
                    "user_email": profile.get("emailAddresses", [{}])[0].get(
                        "value", "unknown"
                    ),
                    "is_authenticated": True,
                }
            )

            st.query_params.clear()
            st.rerun()
            return True

        except Exception as e:
            st.error(f"Authentication error: {e}")
            reset_auth_session()
            return False

    # Show login button
    if not st.session_state.google_auth["is_authenticated"]:
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="false",
        )

        st.markdown("### Sign in Required")
        st.markdown(
            "To use this app, please sign in with your Google account."
        )
        if st.button("🔐 Sign in with Google"):
            st.markdown(f"[Click here to authenticate]({auth_url})")
        return False


def get_authenticated_service():
    auth_data = st.session_state.get("google_auth", {})
    if not auth_data.get("is_authenticated") or not auth_data.get("creds"):
        return None, None, None

    try:
        drive_service = build(
            "drive",
            "v3",
            credentials=auth_data["creds"],
            static_discovery=False,
        )
        return drive_service, auth_data["user_name"], auth_data["user_email"]
    except Exception as e:
        st.error(f"Failed to create Google Drive service: {e}")
        reset_auth_session()
        return None, None, None
