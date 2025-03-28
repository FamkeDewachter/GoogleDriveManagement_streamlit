# auth_view.py
import streamlit as st


class AuthView:
    @staticmethod
    def show_login(title, message, auth_url):
        st.title(title)
        st.markdown(message)
        st.button(
            "🔐 Sign in with Google",
            on_click=lambda: st.markdown(
                f"[Click here if not redirected]({auth_url})"
            ),
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
