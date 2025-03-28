from models.google_drive_utils import (
    gds_get_files,
    gds_get_versions_of_a_file,
    download_file_version,
    gds_get_all_drives,
    gds_get_subfolders_hierarchical,
)
import streamlit as st


class SelectionHandler:
    def __init__(self, drive_service, user_name):
        """Initialize the selection handler with
        the drive service and selected drive ID."""
        self.drive_service = drive_service
        self.user_name = user_name

    def get_all_drives_for_display(self):
        """
        Get all drives from Google Drive
        and return them as a sorted list of dictionaries.

        Returns:
            list: A sorted list of dictionaries with "id" and "name" keys.
        """
        st.write(
            "drive_service in get all ddrives for isplay", self.drive_service
        )
        drives = gds_get_all_drives(self.drive_service)

        # Convert drives to list of dictionaries
        drives_dict = [
            {"id": drive["id"], "name": drive["name"]} for drive in drives
        ]

        # Sort drives by name
        drives_sorted = sorted(drives_dict, key=lambda x: x["name"])

        return drives_sorted

    def get_folders_with_max_depth(self, drive_id, max_depth=2):
        """
        Retrieve the most recent folder from Google Drive.

        Args:
            drive_id (str): The ID of the drive to search for folders.
        """
        project_folders = gds_get_subfolders_hierarchical(
            self.drive_service, drive_id, max_depth=max_depth
        )
        return project_folders

    def get_folders_matching_search(self, drive_id, search_term):
        """
        Retrieve folders from Google Drive and return them as a list of dictionaries
        with keys "id" and "name".

        Args:
            drive_id (str): The ID of the drive to search for folders.
            search_term (str): The search term to filter folders by name.

        Returns:
            list: A list of dictionaries containing folder names and IDs.
                Returns None if no search term is provided or if an error occurs.
        """
        if not search_term:
            return None

        try:
            folders = gds_get_subfolders_hierarchical(
                self.drive_service, drive_id, search_term=search_term
            )
            return folders
        except Exception as e:
            st.error(f"Failed to retrieve folders matching search term: {e}")
            return None

    def retrieve_files(self):
        """Retrieve files from Google Drive."""
        drive_id = st.session_state.selected_drive["id"]
        files = gds_get_files(self.drive_service, drive_id)
        return files

    def retrieve_versions(self, file_id):
        """Retrieve versions of a specific file."""
        versions = gds_get_versions_of_a_file(self.drive_service, file_id)
        return versions

    def download_file_version(self, file_id, version_id):
        """Download a specific version of a file."""
        file_content = download_file_version(
            self.drive_service, file_id, version_id
        )
        return file_content
