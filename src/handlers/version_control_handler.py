from models.google_drive_utils import (
    gds_get_files,
    gds_get_versions_of_a_file,
    gds_upload_version,
    gds_get_current_version,
    gds_revert_version,
    gds_delete_file,
    gds_get_folders_info,
    gds_move_file,
    gds_get_subfolders_hierarchical,
    gds_delete_version,
    gds_upload_file,
    gds_restore_file,
    gds_get_trashed_files,
    gds_get_file_revision_as_bytes,
    gds_delete_old_versions,
    gds_rename_file,
    gds_update_keep_forever_version,
    gds_get_most_recent_files_recursive,
)
from models.general_utils import (
    format_size,
    format_date,
    format_mime_type,
)
from models.mongodb_model import (
    mongo_get_version,
    mongo_save_version,
    mongo_delete_version,
)
import zipfile
from io import BytesIO


class VersionControlHandler:
    def __init__(self, drive_service, user_name):
        """
        Initialize the version control handler
        with the drive service and user info.

        Args:
            drive_service (obj): The Google Drive service instance.
            user_name (str): The name of the user.
        """
        self.drive_service = drive_service
        self.user_name = user_name

    def create_zip_file(self, file_data_list):
        """
        Creates a zip file in memory from multiple files.

        Args:
            file_data_list (list): A list of dictionaries
            containing file data with keys 'file_name' and 'file_bytes'.

        Returns:
            BytesIO: A BytesIO object containing the zip file.
        """
        zip_buffer = BytesIO()
        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            for file_data in file_data_list:
                file_name = file_data["file_name"]
                file_bytes = file_data["file_bytes"]
                if isinstance(file_bytes, BytesIO):
                    file_bytes = file_bytes.getvalue()
                zip_file.writestr(file_name, file_bytes)
        zip_buffer.seek(0)
        return zip_buffer

    def delete_file(self, file_id, delete_permanently):
        """
        Deletes a file from Google Drive.

        Args:
            file_id (str): The ID of the file to delete.
            delete_permanently (bool): Whether to delete the file permanently.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """
        if gds_delete_file(
            self.drive_service,
            file_id,
            delete_permanently=delete_permanently,
        ):
            success = True
            if delete_permanently:
                message = "File permanently deleted successfully."
            else:
                message = "File moved to trash successfully."
        else:
            success = False
            message = "Failed to delete file."

        return success, message

    def upload_version(
        self,
        file,
        version_to_upload,
        description,
        keep_forever,
        change_file_type,
        keep_only_latest_version,
    ):
        """
        Uploads a new version of a file to Google Drive.

        Args:
            file (dict): The file on Google Drive to upload the version to.
            version_to_upload (BytesIO): The file to upload.
            description (str): The description of the version.
            keep_forever (bool): Whether to keep the file forever.
            change_file_type (bool): Whether to change the file type
            of the file to match the new version.
            keep_only_latest_version (bool): Whether to keep only the latest
            version.

        Returns:
            tuple: A tuple containing a
            boolean indicating success and a message.
        """
        # Step 1: Upload the new version to Google Drive
        try:
            curr_file_id = file["id"]
            curr_file_name = file["name"]
            curr_file_type = file["mimeType"]
            gds_upload_version(
                self.drive_service,
                curr_file_id,
                curr_file_name,
                version_to_upload,
                change_file_type,
                keep_forever,
                current_mime_type=curr_file_type,
            )

            if keep_only_latest_version:
                gds_delete_old_versions(self.drive_service, curr_file_id)

        except Exception as e:
            success = False
            message = f"Failed to upload version to Google Drive: {str(e)}"
            return success, message

        # Step 2: Save initial version to MongoDB
        try:
            # Upload the description of the new version to MongoDB
            curr_version = gds_get_current_version(
                self.drive_service, curr_file_id
            )
            curr_version_id = curr_version["id"]
            curr_version_name = curr_version["originalFilename"]

            mongo_save_version(
                curr_file_id, curr_version_id, curr_version_name, description
            )

        except Exception as e:
            success = False
            message = f"Failed to save data of version to mongoDB: {str(e)}"
            return success, message

        # Determine the message based on the options selected
        success = True
        message = "Version uploaded successfully."

        if keep_forever:
            message += " The file will be kept forever."

        if keep_only_latest_version:
            message += (
                " Only the latest version will be kept, and older versions "
                "have been deleted."
            )

        return success, message

    def get_files_from_trash(self, drive_id):
        """
        Retrieves files from the trash in Google Drive.

        Args:
            drive_id (str): The ID of the Google Drive.

        Returns:
            list: A list of files with formatted details.
        """
        # get files starting from the specified folder
        files = gds_get_trashed_files(
            service=self.drive_service,
            drive_id=drive_id,
            fields="mimeType, trashed, parents, modifiedTime,"
            " createdTime, size, webViewLink, "
            "webContentLink, id, name, description",
        )

        return files

    def add_folder_name_to_files(self, files, folder_info):
        """
        Adds the folder name to each file.

        Args:
            files (list): A list of files.
            folder_info (dict): A dictionary mapping
            folder IDs to folder names.
        """
        # Map folder IDs to their names

    def restore_file(self, file_id):
        """
        Restore a file from the trash on Google Drive.

        Args:
            file_id (str): The ID of the file to restore.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """
        if gds_restore_file(self.drive_service, file_id):
            success = True
            message = "File restored successfully."

        else:
            success = False
            message = "Failed to restore file."

        return success, message

    def revert_version(self, file, version_to_revert, description):
        """
        Reverts a file to a specific version on Google Drive.

        Args:
            file (dict): The file on Google Drive to revert a version of.
            version_to_revert (dict): The version of the file to revert to.
            description (str): The description of
            the version written by the user.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """
        file_id = file["id"]
        file_name = file["name"]
        version_id = version_to_revert["id"]
        version_name = version_to_revert["originalFilename"]

        # Step 1: Revert the file to the selected version on Google Drive
        if not (
            gds_revert_version(
                self.drive_service,
                file_id,
                file_name,
                version_id,
                version_name,
            )
        ):
            success = False
            message = "Failed to revert version on Google Drive"
            return success, message

        # Step 2: Update the versions in MongoDB
        try:
            auto_description = (
                f"Reverted from version {version_to_revert['versionNumber']} "
                f"'{version_name}'."
            )

            full_description = (
                f"{description}\n({auto_description})"
                if description
                else auto_description
            )

            # Get the current version of the file(the one you just uploaded)
            new_version = gds_get_current_version(self.drive_service, file_id)
            new_version_id = new_version["id"]
            new_Version_name = new_version["originalFilename"]

            mongo_save_version(
                file_id,
                new_version_id,
                new_Version_name,
                full_description,
            )

        except Exception as e:
            return (
                False,
                f"Failed to update version in MongoDB when reverting: "
                f"{str(e)}",
            )

        success = True
        message = "File reverted successfully to the selected version."
        return success, message

    def get_most_recent_files(
        self, drive_id, folder_id, fields, max_results=20
    ):
        """Wrapper for gds_get_most_recent_files_recursive."""
        return gds_get_most_recent_files_recursive(
            self.drive_service,
            drive_id,
            folder_id=folder_id,
            max_results=max_results,
            fields=fields,
        )

    def get_files_from_folder(self, drive_id, folder_id, search_term, fields):
        """
        Retrieves files from a specified folder in Google Drive.

        Args:
            drive_id (str): The ID of the Google Drive.
            folder_id (str): The ID of the folder.
            search_term (str): The search term to filter files.
            fields (str): The fields to retrieve for each file.

        Returns:
            list: A list of files with formatted details.
        """
        # get files starting from the specified folder
        files = gds_get_files(
            service=self.drive_service,
            drive_id=drive_id,
            fields=fields,
            folder_id=folder_id,
            search_term=search_term if search_term else None,
        )

        return files

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

    def format_files_for_display(self, files, folder_info):
        """
        Adds the folder name and folder ID to
        each file and formats some keys for display.

        Args:
            files (list): A list of files.
            folder_info (dict): A dictionary mapping
            folder IDs to folder names.

        Returns:
            list: A list of files with formatted details.
        """
        # Map folder IDs to their names
        folder_names = {folder["id"]: folder["name"] for folder in folder_info}

        # Add the folder name and folder ID to each file
        for file in files:
            if file.get("parents"):

                file["folder_name"] = folder_names.get(
                    file["parents"][0], "N/A"
                )
                file["folder_id"] = file["parents"][0]

                # remove the parents key
                file.pop("parents")
            else:
                file["folder_name"] = "N/A"
                file["folder_id"] = None

        # Format the files for display
        for file in files:
            if "size" in file:
                file["size"] = format_size(file["size"])
            if "createdTime" in file:
                file["createdTime"] = format_date(file["createdTime"])
            if "modifiedTime" in file:
                file["modifiedTime"] = format_date(file["modifiedTime"])
            if "mimeType" in file:
                file["mimeType"] = format_mime_type(file["mimeType"])

        return files

    def get_versions_of_file_for_display(self, file_id):
        """
        Retrieves versions of a specified file from Google Drive.

        Args:
            file_id (str): The ID of the file.

        Returns:
            list: A list of versions with formatted details and descriptions.
        """

        versions = gds_get_versions_of_a_file(
            self.drive_service,
            file_id,
            fields=(
                "id, originalFilename, modifiedTime,"
                " size, mimeType, keepForever"
            ),
        )

        # Format the versions for display
        for version in versions:
            if "size" in version:
                version["size"] = format_size(version["size"])
            if "modifiedTime" in version:
                version["modifiedTime"] = format_date(version["modifiedTime"])
            if "mimeType" in version:
                version["mimeType"] = format_mime_type(version["mimeType"])

        # Add description to the versions
        # cause these are not saved on the drive
        for version in versions:
            version_on_mongo = mongo_get_version(file_id, version["id"])

            # Add description key to version
            version["description"] = "N/A"

            # Check if version exists on MongoDB, if so update description
            if version_on_mongo is not None:
                if "description" in version_on_mongo:
                    version["description"] = version_on_mongo["description"]

        # Sort versions by created time so oldest is version 1
        # If createdTime is "N/A", it will be placed even
        # before the first version
        versions.sort(
            key=lambda x: (
                x["modifiedTime"] != "N/A",
                x["modifiedTime"] if x["modifiedTime"] != "N/A" else "",
            )
        )
        for i, version in enumerate(versions, start=1):
            version["versionNumber"] = i

        return versions

    def move_file(self, file_id, curr_folder_id, new_folder_id):
        """
        Moves a file to a new folder in Google Drive.

        Args:
            file_id (str): The ID of the file to move.
            curr_folder_id (str): The ID of the current folder.
            new_folder_id (str): The ID of the new folder.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """
        try:
            gds_move_file(
                self.drive_service,
                file_id,
                curr_folder_id,
                new_folder_id,
            )
            success = True
            message = "File moved successfully."

        except Exception as e:
            success = False
            message = f"Failed to move file: {str(e)}"

        return success, message

    def upload_file(self, file, folder, description):
        """
        Uploads a file to Google Drive.

        Args:
            file (BytesIO): The file to upload.
            folder (dict): The folder to upload the file to.
            description (str): The description of the file.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """

        # Step 1: Upload the file to Google Drive
        try:
            folder_id = folder["id"]
            uploaded_file = gds_upload_file(
                self.drive_service,
                file,
                folder_id,
                description,
                fields="id, name",
            )
            uploaded_file_id = uploaded_file["id"]

        except Exception as e:
            # Handle any errors during the upload process
            success = False
            message = f"Failed to upload file to Google Drive: {str(e)}"
            return success, message

        # Step 2: Save the 1st version of the file to MongoDB
        try:
            # When uploading a file you cant get the current
            # version id directly from the fields,
            # so we have to look for it again
            revisions_of_file = gds_get_versions_of_a_file(
                self.drive_service,
                uploaded_file_id,
                fields="id, originalFilename",
            )
            curr_version_id = revisions_of_file[0]["id"]
            curr_version_name = revisions_of_file[0]["originalFilename"]

            # Save the description to MongoDB to the file
            # And save the first version of the file
            mongo_save_version(
                uploaded_file_id,
                curr_version_id,
                curr_version_name,
                description,
            )

        except Exception as e:
            success = False
            message = f"Failed to save description to MongoDB: {str(e)}"
            return success, message

        folder_name = folder["name"]
        success = True
        message = (
            f"File '{file.name}' uploaded successfully to '{folder_name}'"
        )
        return success, message

    def get_subfolders_hierarchically(self, drive_id, root_folder_id):
        """
        Retrieves subfolders of a specified folder in Google Drive.

        Args:
            drive_id (str): The ID of the Google Drive.
            root_folder_id (str): The ID of the folder.

        Returns:
            list: A list of subfolders with hierarchical structure.
        """
        try:
            subfolders = gds_get_subfolders_hierarchical(
                self.drive_service, drive_id, folder_id=root_folder_id
            )

            return subfolders

        except Exception as e:
            print(f"Error getting subfolders: {str(e)}")
            return []

    def delete_version(self, file_id, version_id):
        """
        Deletes a version of a file from Google Drive.

        Args:
            file_id (str): The ID of the file.
            version_id (str): The ID of the version.

        Returns:
            tuple: A tuple containing a
            boolean indicating success and a message.
        """
        # Delete the version from Google Drive
        if gds_delete_version(self.drive_service, file_id, version_id):

            # Delete the version from MongoDB
            mongo_delete_version(file_id, version_id)

            success = True
            message = "Version deleted successfully."
        else:
            success = False
            message = "Failed to delete version."

        return success, message

    def get_revision_as_bytes(self, file_id, version_id):
        """
        Retrieves a file revision as bytes from Google Drive.

        Args:
            file_id (str): The ID of the file.
            version_id (str): The ID of the version.

        Returns:
            tuple: A tuple containing the file
            revision as bytes and the mime type.
        """
        try:
            file_bytes, mime_type = gds_get_file_revision_as_bytes(
                self.drive_service, file_id, version_id
            )
            return file_bytes, mime_type
        except Exception as e:
            print(f"Error getting revision as bytes: {str(e)}")
            return None, None

    def rename_file(self, file_id, new_name):
        """
        Renames a file on Google Drive.

        Args:
            file_id (str): The ID of the file.
            new_name (str): The new name of the file.

        Returns:
            tuple: A tuple containing a boolean
            indicating success and a message.
        """
        try:
            gds_rename_file(self.drive_service, file_id, new_name)
            success = True
            message = "File renamed successfully."
        except Exception as e:
            success = False
            message = f"Failed to rename file: {str(e)}"

        return success, message

    def update_version_keep_forever(self, file_id, version_id, keep_forever):
        """
        Updates the keep forever status of a version of a file on Google Drive.

        Args:
            file_id (str): The ID of the file.
            version_id (str): The ID of the version.
            keep_forever (bool): Whether to keep the version forever.

        Returns:
            tuple: A tuple containing a
            boolean indicating success and a message.
        """
        try:
            gds_update_keep_forever_version(
                self.drive_service, file_id, version_id, keep_forever
            )
            success = True
            message = "Keep forever status updated successfully."
            return success, message
        except Exception as e:
            success = False
            message = f"Failed to update keep forever status: {str(e)}"
            return success, message
