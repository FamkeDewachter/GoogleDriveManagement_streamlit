# main_streamlit.py
import streamlit as st
import os
from controllers.main_controller import MainController
from models.auth import authenticate_user, get_authenticated_service

# Configure for production
if os.getenv("IS_PRODUCTION", "false").lower() == "true":
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="expanded",
        page_title="Your App Name",
    )
else:
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")


def show_login_screen():
    """Show the login screen and handle authentication."""
    st.title("Welcome to the Application")
    st.write("Please sign in to continue")

    if authenticate_user():
        st.session_state.authenticated = True
        st.rerun()


def show_main_app():
    """Show the main application after authentication."""
    try:
        # Get the authenticated service
        drive_service, user_name, user_email = get_authenticated_service()

        if not drive_service or not user_name:
            st.error("Authentication failed. Please try again.")
            st.session_state.authenticated = False
            st.rerun()
            return

        app = MainController()
        app.start()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.stop()


if __name__ == "__main__":
    # Check if user is authenticated
    if not st.session_state.get("authenticated", False):
        show_login_screen()
    else:
        show_main_app()
