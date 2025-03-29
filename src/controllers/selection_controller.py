from views.selection_ui import SelectionUI
from handlers.selection_handler import SelectionHandler
import streamlit as st


class SelectionController:
    def __init__(self, drive_service, user_name):
        """
        Initialize the Selection Controller.

        Args:
            drive_service: The Google Drive service instance.
            user_name (str): The name of the user.
        """
        self.ui = SelectionUI()
        self.handler = SelectionHandler(drive_service, user_name)
        self._initialize_session_state()

    def _initialize_session_state(self):
        """
        Initializes all required session state variables with default values.
        """
        defaults = {
            # Drive selection states
            "all_drives": None,
            "selected_drive": None,
            # Folder selection states
            "all_project_folders": None,
            "searched_folders": [],
            "last_search_term": None,
            "selected_project_folder": None,
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def start(self):
        """
        Start the Selection Controller.
        """
        st.sidebar.markdown("---")

        # Add a collapsible section for "Options" or "Settings"
        with st.sidebar.expander("⚙️ **Settings**", expanded=True):
            self._handle_and_display_drives()
            self._handle_and_display_project_folders()

    def _handle_and_display_drives(self):
        """
        Handle and display the drives in a user-friendly way.
        """
        st.markdown("### Select a Shared Drive")

        # Get drives if not in session state
        if st.session_state.all_drives is None:
            st.session_state.all_drives = (
                self.handler.get_all_drives_for_display()
            )

        if not st.session_state.all_drives:
            st.error("No shared drives found. Please check your permissions.")
            self.ui.show_message(
                "No shared drives found, this app requires at least one shared drive.",
                message_type="error",
            )
            return

        # Always display the select box with drives from session state
        new_drive_selection = self.ui.display_selectbox_drives(
            key="selectbox_drives",
            drives=st.session_state.all_drives,
        )

        # Clear cached folders if drive changes
        if (
            st.session_state.selected_drive is not None
            and st.session_state.selected_drive != new_drive_selection
        ):
            self._clear_folder_session_state()

        st.session_state.selected_drive = new_drive_selection

    def _handle_and_display_project_folders(self):
        """
        Handle and display the project folders in a user-friendly way.
        """
        st.markdown("### Select a Project Folder")

        if not st.session_state.selected_drive:
            self.ui.show_message(
                "Please select a shared drive first.", message_type="info"
            )
            return

        drive_id = st.session_state.selected_drive["id"]

        # Display a search bar
        search_term = self.ui.display_search_bar(
            key="search_project_folders",
            label="Search project folder by name:",
            placeholder="Type folder name to search...",
        )

        # Only search when there's a search term and it has changed
        if search_term and search_term != st.session_state.last_search_term:
            folders_to_display = self.handler.get_folders_matching_search(
                drive_id, search_term
            )
            st.session_state.last_search_term = search_term
            st.session_state.searched_folders = folders_to_display

        # Use the cached results if available
        folders_to_display = st.session_state.searched_folders

        if search_term:
            if not folders_to_display:
                self.ui.show_message(
                    "No folders found matching your search. Try a different name.",
                    message_type="info",
                )
                return
        else:
            # When no search term, show a message to search
            self.ui.show_message(
                "Please search for a folder by name to find your project.",
                message_type="info",
            )
            return

        # Show the folders in a selectbox
        new_folder_selection = self.ui.display_selectbox_folders(
            key="select_project_folder",
            folders=folders_to_display,
        )

        # Save the selected folder in the session state
        if new_folder_selection:
            new_folder_selection["depth"] = (
                0  # Reset depth for selected folder
            )
            st.session_state.selected_project_folder = new_folder_selection

    def _clear_folder_session_state(self):
        """Clears all session state related to folder selection."""
        keys_to_clear = [
            "all_project_folders",
            "searched_folders",
            "last_search_term",
            "selected_project_folder",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = (
                    None if key != "searched_folders" else []
                )
