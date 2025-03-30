# auth_view.py
import streamlit as st


class AuthView:
    @staticmethod
    def show_login(title, message, auth_url):
        st.title(title)
        st.markdown(message)

        # Use a direct link with target="_blank" to open in new tab
        st.markdown(
            f"""
            <a href="{auth_url}" target="_blank" style="
                display: inline-block;
                padding: 0.5em 1em;
                color: white;
                background-color: #4285F4;
                border: none;
                border-radius: 4px;
                text-decoration: none;
                font-weight: bold;
            ">
                🔐 Sign in with Google
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "ℹ️ After signing in, you'll be redirected back to the application."
        )

    @staticmethod
    def show_error(message):
        st.error(message)

    @staticmethod
    def show_warning(message):
        st.warning(message)

    @staticmethod
    def configure_page(wide_layout=True, expanded_sidebar=True, title=None):
        st.set_page_config(
            layout="wide" if wide_layout else "centered",
            initial_sidebar_state=(
                "expanded" if expanded_sidebar else "collapsed"
            ),
            page_title=title or "GDrive Asset Manager",
        )
