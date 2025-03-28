import streamlit as st
from controllers.main_controller import MainController
from models.auth import (
    get_auth_url,
    handle_oauth_callback,
    check_existing_auth,
)


def main():
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

    # Initialize session state for auth if not exists
    if "google_auth" not in st.session_state:
        st.session_state.google_auth = {
            "creds": None,
            "user_name": None,
            "user_email": None,
        }

    # Check for existing valid credentials
    existing_auth = check_existing_auth()
    if existing_auth:
        st.session_state.google_auth.update(
            {
                "creds": existing_auth["drive_service"],
                "user_name": existing_auth["user_name"],
                "user_email": existing_auth["user_email"],
            }
        )

    # Handle OAuth callback if code is in URL
    query_params = st.query_params()
    if "code" in query_params:
        try:
            auth_data = handle_oauth_callback()
            st.session_state.google_auth.update(auth_data)
            st.experimental_set_query_params()  # Clear URL params
            st.rerun()  # Refresh to load authenticated state
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return

    # Show auth screen if not authenticated
    if not st.session_state.google_auth["creds"]:
        st.title("Google Drive Management")
        st.markdown("### Please authenticate with Google to continue")
        auth_url = get_auth_url()
        st.markdown(
            f"""
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color: #4285F4;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;">
                    Sign in with Google
                </button>
            </a>
        """,
            unsafe_allow_html=True,
        )
        return

    # Run main app if authenticated
    app = MainController(
        drive_service=st.session_state.google_auth["creds"],
        user_name=st.session_state.google_auth["user_name"],
        user_email=st.session_state.google_auth["user_email"],
    )
    app.start()


if __name__ == "__main__":
    main()
