import streamlit as st
import os
from controllers.main_controller import MainController

# Configure for production
if os.getenv("IS_PRODUCTION", "false").lower() == "true":
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="expanded",
        page_title="Your App Name",
    )
else:
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

if __name__ == "__main__":
    try:
        app = MainController()
        app.start()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.stop()
