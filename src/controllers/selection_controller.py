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

        # Initialize drives in session state if not present
        if "all_drives" not in st.session_state:
            st.write("Fetching shared drives... This may take a few seconds.")
            st.session_state.all_drives = (
                self.handler.get_all_drives_for_display()
            )
            st.session_state.selected_drive = None
        if not st.session_state.all_drives:
            st.write("No shared drives found. Please check your permissions.")
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
            "selected_drive" in st.session_state
            and st.session_state.selected_drive != new_drive_selection
        ):
            st.session_state.all_project_folders = None
            st.session_state.selected_project_folder = None

        st.session_state.selected_drive = new_drive_selection

    def _handle_and_display_project_folders(self):
        """
        Handle and display the project folders in a user-friendly way.
        """
        st.markdown("### Select a Project Folder")

        if (
            "selected_drive" not in st.session_state
            or not st.session_state.selected_drive
        ):
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

        # Initialize folders in session state if not present
        if "all_project_folders" not in st.session_state:
            st.session_state.all_project_folders = None

        # Only search when there's a search term
        if search_term:
            folders_to_display = self.handler.get_folders_matching_search(
                drive_id, search_term
            )

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
