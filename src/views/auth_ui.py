# auth_view.py
import streamlit as st
import streamlit.components.v1 as components


class AuthView:
    @staticmethod
    def show_login(title, message, auth_url):
        st.title(title)
        st.markdown(message)

        if st.button("🔐 Sign in with Google"):
            # Meta refresh to redirect
            st.markdown(
                f"""
                <meta http-equiv="refresh" content="0; url={auth_url}" />
                """,
                unsafe_allow_html=True,
            )
            # Fallback link
            st.markdown(
                f"⚠️ If you were not redirected, [click here to sign in manually]({auth_url})."
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
