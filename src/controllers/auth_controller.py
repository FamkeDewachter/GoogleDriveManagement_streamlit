# auth_controller.py
import streamlit as st
import os
from handlers.auth_handler import AuthHandler
from views.auth_ui import AuthView
from controllers.main_controller import MainController


class AuthController:
    def __init__(self):
        self.configure_app()
        self.handler = AuthHandler(
            client_config={
                "web": {
                    "client_id": st.secrets["google"]["client_id"],
                    "client_secret": st.secrets["google"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [st.secrets["google"]["redirect_uri"]],
                }
            },
            redirect_uri=st.secrets["google"]["redirect_uri"],
        )
        self.view = AuthView()
        self.initialize_session()

    def configure_app(self):
        AuthView.configure_page(
            wide_layout=True,
            expanded_sidebar=True,
            title=(
                "GDrive Asset Manager" if os.getenv("IS_PRODUCTION") else None
            ),
        )

    def initialize_session(self):
        if "auth" not in st.session_state:
            st.session_state.auth = {
                "credentials": None,
                "user": None,
                "authenticated": False,
            }

    def start(self):
        query_params = st.query_params.to_dict()

        # Handle OAuth callback
        if "code" in query_params:
            self.handle_callback(query_params)
            return

        # Check existing auth
        if st.session_state.auth["authenticated"]:
            self.start_main_app()
        else:
            self.show_login()

    def handle_callback(self, query_params):
        try:
            self.handler.fetch_token(query_params["code"])
            creds = self.handler.get_credentials()
            user = self.handler.get_user_info(creds)

            st.session_state.auth.update(
                {"credentials": creds, "user": user, "authenticated": True}
            )

            st.query_params.clear()
            st.rerun()

        except Exception as e:
            self.view.show_error(f"Authentication failed: {str(e)}")
            self.reset_session()

    def start_main_app(self):
        drive_service = self.handler.build_drive_service(
            st.session_state.auth["credentials"]
        )

        if not drive_service:
            self.view.show_error("Failed to initialize Drive service")
            self.reset_session()
            return

        MainController(
            drive_service,
            st.session_state.auth["user"]["name"],
            st.session_state.auth["user"]["email"],
        ).start()

    def show_login(self):
        self.view.show_login(
            title="📁 GDrive Asset Manager",
            message="Welcome! Please log in with your Google account.",
            auth_url=self.handler.get_auth_url(),
        )

    def reset_session(self):
        st.session_state.auth = {
            "credentials": None,
            "user": None,
            "authenticated": False,
        }
        st.rerun()
