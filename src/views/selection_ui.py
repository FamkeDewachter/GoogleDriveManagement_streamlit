import streamlit as st
from models.general_utils import format_folder_options


class SelectionUI:
    def __init__(self):
        """Initialize the selection UI."""
        pass

    def display_selectbox_drives(
        self,
        key,
        drives,
    ):
        """Display a selectbox for shared drives."""
        if not drives:
            self.show_message("No drives available.", message_type="warning")
            return None

        # Define a format function to display the drive name
        def format_drive(drive):
            return drive["name"]

        # Display the selectbox with the custom format function
        selected_drive = st.selectbox(
            "Select a Shared Drive",
            drives,
            format_func=format_drive,
            key=key,
            index=0,
        )

        # Return the selected drive dictionary
        return selected_drive

    def display_selectbox_folders(self, key, folders):
        """Display a selectbox for project folders."""
        if not folders:
            self.show_message(
                "No project folders available, make sure to have at least one folder in your drive.",
                message_type="warning",
            )

        def format_folder(folder):
            return format_folder_options(folder)

        # Ensure selectbox doesn't break on empty list
        selected_folder = st.selectbox(
            "Select a Project Folder",
            folders,
            format_func=format_folder,
            key=key,
            index=0,
        )

        return selected_folder

    def show_message(self, message, message_type="info"):
        """Display a message to the user."""
        if message_type == "error":
            st.error(message)
        elif message_type == "warning":
            st.warning(message)
        else:
            st.info(message)

    def display_download_button(self, file_content, file_name):
        """Display a download button in the sidebar."""
        st.download_button(
            label=f"Download {file_name}",
            data=file_content,
            file_name=file_name,
            mime="application/octet-stream",
            key="download_button",
        )

    def display_search_bar(
        self,
        key,
        label="Search:",
        placeholder="Search...",
    ):
        """Display a search bar for searching project folders."""
        search_term = st.text_input(
            label,
            key=key,
            placeholder=placeholder,
        )
        return search_term
