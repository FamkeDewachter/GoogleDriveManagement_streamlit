from models.auth import authenticate_google_drive_web
from controllers.comment_controller import CommentController
from controllers.version_control_controller import VersionControlController
from controllers.selection_controller import SelectionController
from streamlit_option_menu import option_menu
import streamlit as st


class MainController:
    def __init__(self):
        """
        Initialize the Main Controller.
        """
        self.drive_service, self.user_name, self.user_email = (
            authenticate_google_drive_web()
        )

        # Initialize the Selection Controller first
        self.selection_controller = SelectionController(
            self.drive_service, self.user_name
        )

        # Initialize other controllers only if needed
        self.comment_controller = None
        self.version_controller = None

    def start(self):
        """
        Start the Main Controller and display the navigation sidebar.
        """
        # Set default page to "Version Control"
        if "selected_page" not in st.session_state:
            st.session_state["selected_page"] = "Version Control"

        # Display the navigation sidebar first to capture the selection
        self._display_navigation_sidebar()

        # Store the current page after potential update from sidebar
        current_page = st.session_state["selected_page"]
        previous_page = st.session_state.get("previous_page", current_page)

        # Clear relevant session state when switching pages
        if previous_page != current_page:
            self._clear_page_switch_state(previous_page, current_page)

        # Update previous page
        st.session_state["previous_page"] = current_page

        # Rest of your existing code...
        self.selection_controller.start()

        if not self._has_valid_selections():
            return

        self._init_other_controllers()

        if current_page == "Comments":
            self.comment_controller.start(width_ratio=3)
        elif current_page == "Version Control":
            self.version_controller.start()

    def _clear_page_switch_state(self, previous_page, current_page):
        """Clear relevant session state when switching between pages."""
        if previous_page == "Version Control" and current_page == "Comments":
            # Clear file and version selection state when coming back to Comments
            keys_to_clear = [
                "selected_file",
                "selected_version",
                "comments",
                "all_files",
                "all_versions",
                "filter_criteria",
            ]
            for key in keys_to_clear:
                st.session_state.pop(key, None)

    def _has_valid_selections(self):
        """
        Check if both drive and folder are selected.
        Returns True if both are selected, False otherwise.
        """
        if (
            "selected_drive" not in st.session_state
            or not st.session_state.selected_drive
            or "selected_project_folder" not in st.session_state
            or not st.session_state.selected_project_folder
        ):
            st.warning(
                "Please select both a shared drive and a project folder to continue."
            )
            return False
        return True

    def _init_other_controllers(self):
        """
        Initialize the other controllers only when needed.
        """
        if self.comment_controller is None:
            self.comment_controller = CommentController(
                self.drive_service, self.user_name
            )
        if self.version_controller is None:
            self.version_controller = VersionControlController(
                self.drive_service, self.user_name
            )

    def _display_navigation_sidebar(self):
        """
        Display the navigation sidebar with links to different pages.
        """
        with st.sidebar:
            st.title("Features")

            # Use the current session state value as the default
            selected_page = option_menu(
                menu_title=None,
                options=["Version Control", "Comments"],
                icons=["clock-history", "chat"],
                default_index=(
                    0
                    if st.session_state["selected_page"] == "Version Control"
                    else 1
                ),
                orientation="vertical",
            )

            # Immediately update the session state with the new selection
            st.session_state["selected_page"] = selected_page
