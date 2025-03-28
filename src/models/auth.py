import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define consistent scopes (order matters for comparison)
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def authenticate_google_drive_web():
    # Initialize session state
    if "google_auth" not in st.session_state:
        st.session_state.google_auth = {
            "creds": None,
            "user_name": None,
            "user_email": None,
            "requested_scopes": None,
        }

    # Return cached credentials if valid
    if (
        st.session_state.google_auth["creds"]
        and st.session_state.google_auth["creds"].valid
    ):
        try:
            if set(st.session_state.google_auth["creds"].scopes or []) != set(
                st.session_state.google_auth["requested_scopes"]
            ):
                raise ValueError("Scope mismatch detected")

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
        except (HttpError, ValueError) as e:
            st.error(f"Session validation failed: {e}")
            st.session_state.google_auth = {
                "creds": None,
                "user_name": None,
                "user_email": None,
                "requested_scopes": None,
            }
            st.rerun()

    try:
        redirect_uri = "https://gdrive-management.streamlit.app/"

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": st.secrets["google"]["client_id"],
                    "client_secret": st.secrets["google"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        st.session_state.google_auth["requested_scopes"] = SCOPES

        # Get query parameters
        query_params = st.query_params.to_dict()
        if "code" in query_params:
            try:
                code = query_params["code"]
                flow.fetch_token(code=code)
                creds = flow.credentials

                if set(creds.scopes or []) != set(SCOPES):
                    raise ValueError(
                        f"Scope mismatch. Requested: {SCOPES}, Granted: {creds.scopes}"
                    )

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

                st.session_state.google_auth.update(
                    {
                        "creds": creds,
                        "user_name": profile.get("names", [{}])[0].get(
                            "displayName", "Unknown"
                        ),
                        "user_email": profile.get("emailAddresses", [{}])[
                            0
                        ].get("value", "unknown"),
                    }
                )
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Token exchange failed: {e}")
                st.session_state.google_auth = {
                    "creds": None,
                    "user_name": None,
                    "user_email": None,
                    "requested_scopes": None,
                }
                st.rerun()

        # If not authenticated, show login button
        if not st.session_state.google_auth["creds"]:
            auth_url, _ = flow.authorization_url(
                prompt="consent",
                access_type="offline",
                include_granted_scopes="false",
            )
            if st.button("Login with Google"):
                st.write(
                    f"Please [click here]({auth_url}) to authenticate with Google"
                )
                return None, None, None

        return None, None, None

    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.session_state.google_auth = {
            "creds": None,
            "user_name": None,
            "user_email": None,
            "requested_scopes": None,
        }
        return None, None, None
