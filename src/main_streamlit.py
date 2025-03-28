# main_streamlit.py
from controllers.auth_controller import AuthController

if __name__ == "__main__":
    app = AuthController()
    app.start()
