from models.mongodb_model import (
    mongo_save_new_comment,
    mongo_get_comments_of_version,
    mongo_update_comment_content,
    mongo_delete_comment,
    mongo_update_comment_resolved_status,
    mongo_save_reply,
    mongo_delete_reply,
)
import streamlit as st
from models.google_drive_utils import (
    gds_get_files,
    gds_get_versions_of_a_file,
    gds_get_most_recent_files_recursive,
    gds_get_folders_info,
    gds_download_version_image,
    gds_get_file_revision_as_bytes,
)
from datetime import datetime


class CommentsHandler:
    def __init__(self, drive_service, user_name):
        """Initialize the comments handler
        with the drive service and user info."""
        self.drive_service = drive_service
        self.user_name = user_name

    def get_file_preview_link(self, file_id):
        """Get the preview link
        for a specific version of a file."""
        try:
            file_metadata = (
                self.drive_service.files()
                .get(
                    fileId=file_id,
                    fields="webViewLink, exportLinks",
                    supportsAllDrives=True,
                )
                .execute()
            )
            # Check if the file has exportLinks
            # (e.g., for Google Docs, Sheets, etc.)
            export_links = file_metadata.get("exportLinks", {})

            # If the file has exportLinks, use the appropriate link for preview
            if export_links:
                # For example, use the 'text/html' export link for Google Docs
                preview_link = export_links.get("text/html")
                if preview_link:
                    return preview_link

            # If no exportLinks are available, fall back to the webViewLink
            preview_link = file_metadata.get("webViewLink")
            return preview_link
        except Exception as e:
            st.error(f"An error occurred while fetching the preview link: {e}")
            return None

    def save_new_comment(self, file, version, comment_text):
        """Add a new comment to the selected version of the file."""
        file_id = file["id"]
        version_id = version["id"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_comment = mongo_save_new_comment(
            file_id,
            version_id,
            version["name"],
            self.user_name,
            timestamp,
            comment_text,
        )

        return new_comment

    def delete_comment(self, file, version, comment_id):
        """Delete a comment from the selected version of the file."""
        file_id = file["id"]
        version_id = version["id"]
        mongo_delete_comment(file_id, version_id, comment_id)

    def update_comment_content(self, file, version, comment_id, new_content):
        """Update the content of a comment."""
        file_id = file["id"]
        version_id = version["id"]
        mongo_update_comment_content(
            file_id, version_id, comment_id, new_content
        )

    def get_files_in_project_with_search_term(self, search_term):
        """Retrieve files from Google Drive."""
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]

        files = gds_get_files(
            service=self.drive_service,
            drive_id=drive_id,
            fields=("id, name, parents, modifiedTime"),
            search_term=search_term,
            folder_id=project_folder_id,
        )

        return files

    def get_recent_files_in_project(self, max_results=10):
        """Retrieve the most recent files from Google Drive."""
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]

        recent_files = gds_get_most_recent_files_recursive(
            self.drive_service,
            drive_id,
            folder_id=project_folder_id,
            max_results=max_results,
            fields="id, name, parents, modifiedTime",
        )

        return recent_files

    def get_folders_info(self, folder_ids, fields="id, name"):
        """
        Retrieves information about specified folders in Google Drive.

        Args:
            folder_ids (list): A list of folder IDs.
            fields (str): The fields to retrieve for each folder.

        Returns:
            list: A list of dictionaries containing folder information.
        """
        folder_info = gds_get_folders_info(
            self.drive_service, folder_ids, fields=fields
        )

        return folder_info

    def add_folder_info_to_files(self, files, folders):
        """
        Adds folder_name to each file and renames parents to folder_id.

        Args:
            files: List of file dicts with parents array
            folders: List of folder dicts with id and name

        Returns:
            List of file dicts with folder_id and folder_name added
        """
        # Create a mapping from folder id to folder name for quick lookup
        folder_name_map = {folder["id"]: folder["name"] for folder in folders}

        processed_files = []

        for file in files:
            # Create a copy of the file dict to avoid modifying the original
            file_copy = file.copy()

            # Get the first parent ID (assuming each file only has one parent)
            parent_id = file["parents"][0] if file.get("parents") else None

            # Add folder_id (renamed from parents)
            file_copy["folder_id"] = parent_id

            # Add folder_name if we have it in our mapping
            file_copy["folder_name"] = folder_name_map.get(
                parent_id, "Unknown Folder"
            )

            # Remove the original parents key
            if "parents" in file_copy:
                del file_copy["parents"]

            processed_files.append(file_copy)

        return processed_files

    def get_sorted_versions_of_a_file(self, file_dict):
        """Retrieve versions of a file from Google Drive."""
        file_id = file_dict["id"]
        versions = gds_get_versions_of_a_file(
            self.drive_service,
            file_id,
            fields="id, originalFilename, modifiedTime",
        )

        versions_sorted = sorted(
            versions,
            key=lambda x: x["modifiedTime"],
            reverse=True,
        )

        for version in versions_sorted:
            version["name"] = version.pop("originalFilename")

        if versions_sorted:
            versions_sorted[0]["name"] += " (current version)"

        return versions_sorted

    def get_files_from_folder(self, search_term):
        """Get files from a folder in Google Drive that match a search term."""
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]

        files = gds_get_files(
            service=self.drive_service,
            drive_id=drive_id,
            fields=("id, name"),
            search_term=search_term,
            folder_id=project_folder_id,
        )

        files_formatted = [
            {"id": file["id"], "name": file["name"]} for file in files
        ]

        files_sorted = sorted(files_formatted, key=lambda x: x["name"])
        return files_sorted

    def get_comments_of_version(self, file, version):
        """Retrieve and categorize comments."""
        file_id = file["id"]
        version_id = version["id"]
        comments = mongo_get_comments_of_version(file_id, version_id)

        return comments

    def sort_comments_by_timestamp(self, comments):
        """Sort comments by timestamp."""
        sorted_comments = sorted(
            comments, key=lambda x: x["timestamp"], reverse=True
        )

        return sorted_comments

    def update_resolve_comment(self, file, version, comment_id, resolved):
        """Update the resolved status of a comment."""
        file_id = file["id"]
        version_id = version["id"]
        mongo_update_comment_resolved_status(
            file_id, version_id, comment_id, resolved
        )

    def save_reply(self, file, version, comment_id, reply_text):
        """Save a reply to a comment."""
        file_id = file["id"]
        version_id = version["id"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        reply = mongo_save_reply(
            file_id,
            version_id,
            comment_id,
            self.user_name,
            timestamp,
            reply_text,
        )

        return reply

    def delete_reply(self, file, version, reply_id):
        """Delete a reply to a comment."""
        file_id = file["id"]
        version_id = version["id"]
        mongo_delete_reply(file_id, version_id, reply_id)

    def get_version_media_content(self, file_id, version_id):
        """Get the content of a specific version of a file."""
        content = gds_download_version_image(
            self.drive_service, file_id, version_id
        )

        return content

    def get_version_content(self, file_id, version_id):
        """Get the content of a specific version of a file as bytes with mime type."""
        try:
            file_bytes, mime_type = gds_get_file_revision_as_bytes(
                self.drive_service, file_id, version_id
            )
            return file_bytes, mime_type
        except Exception as e:
            st.error(f"Error getting version content: {str(e)}")
            return None, None
