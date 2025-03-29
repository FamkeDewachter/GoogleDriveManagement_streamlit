import streamlit as st
import os
from handlers.auth_handler import AuthHandler
from views.auth_ui import AuthView
from controllers.main_controller import MainController
import platform


class AuthController:
    def __init__(self):
        self.configure_app()
        self.handler = AuthHandler(
            client_config=self.get_client_config(),
            redirect_uri=self.get_redirect_uri(),
        )
        self.view = AuthView()
        self.initialize_session()

    def get_client_config(self):
        """Get client config from secrets.toml"""
        try:
            return {
                "web": {
                    "client_id": st.secrets.google.web.client_id,
                    "client_secret": st.secrets.google.web.client_secret,
                    "auth_uri": st.secrets.google.web.auth_uri,
                    "token_uri": st.secrets.google.web.token_uri,
                    "redirect_uris": [self.get_redirect_uri()],
                }
            }
        except Exception as e:
            st.error(f"Error loading client config: {str(e)}")
            st.stop()

    def is_production(self):
        """
        Streamlit-specific check for production vs local environment.
        """

        # Check for Streamlit's environment variables
        if os.environ.get("STREAMLIT_SERVER") == "true":
            return True

        # Check platform processor
        if not platform.processor():
            return True

        # Check if running in a common cloud environment
        cloud_env_vars = [
            "K_SERVICE",
            "GAE_ENV",
            "AWS_EXECUTION_ENV",
            "WEBSITE_SITE_NAME",
        ]
        if any(var in os.environ for var in cloud_env_vars):
            return True

        return False

    def get_redirect_uri(self):
        """Use production URI if running on Streamlit Cloud, otherwise local"""
        try:
            is_prod = self.is_production()

            # Get the list of redirect URIs from secrets
            redirect_uris = st.secrets.google.web.redirect_uris

            # Use the first URI for production, second for local (adjust as needed)
            redirect_uri = redirect_uris[0] if is_prod else redirect_uris[1]

            return redirect_uri
        except Exception as e:
            st.error(f"Error getting redirect URI: {str(e)}")
            st.stop()

    def configure_app(self):
        AuthView.configure_page(
            wide_layout=True,
            expanded_sidebar=True,
            title="GDrive Asset Manager",
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
        auth_url = self.handler.get_auth_url()
        self.view.show_login(
            title="📁 GDrive Asset Manager",
            message="Welcome! Please log in with your Google account.",
            auth_url=auth_url,
        )

    def reset_session(self):
        st.session_state.auth = {
            "credentials": None,
            "user": None,
            "authenticated": False,
        }
        st.rerun()
