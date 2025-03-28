import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

from controllers.main_controller import MainController

if __name__ == "__main__":
    app = MainController()
    app.start()
