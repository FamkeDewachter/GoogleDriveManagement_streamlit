from googleapiclient.http import (
    MediaIoBaseDownload,
    MediaIoBaseUpload,
    MediaFileUpload,
)
import io
from googleapiclient.errors import HttpError
import os
import streamlit as st


import mimetypes


def download_file_version(service, file_id, version_id):
    """Download a specific version of a file."""
    print("Downloading file version...")
    request = service.revisions().get_media(
        fileId=file_id, revisionId=version_id
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()


def gds_get_trashed_files(service, drive_id, fields="id, name"):
    """
    Retrieves all files in the trash of a specific Google Drive.

    Args:
        service: Authenticated Google Drive API service instance.
        drive_id (str): The ID of the shared drive (or "My Drive" if None).

    Returns:
        list: A list of dictionaries containing metadata of trashed files.
    """
    try:
        # Query to fetch all trashed files in the specified drive
        query = "trashed = true"

        # Ignore folders and shortcuts
        query += " and mimeType != 'application/vnd.google-apps.folder'"
        query += " and mimeType != 'application/vnd.google-apps.shortcut'"

        # Fetch the trashed files
        results = (
            service.files()
            .list(
                q=query,
                corpora="drive",
                driveId=drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields=f"files({fields})",
            )
            .execute()
        )

        trashed_files = results.get("files", [])
        print(
            f"Found {len(trashed_files)} trashed files in drive '{drive_id}'."
        )
        return trashed_files

    except Exception as e:
        print(f"An error occurred while fetching trashed files: {e}")
        return []


def gds_get_file_revision_as_bytes(drive_service, file_id, revision_id):
    """
    Downloads a specific revision from Google Drive and returns it as a BytesIO buffer.

    Args:
        drive_service: Authenticated Google Drive service instance.
        file_id (str): ID of the file.
        revision_id (str): ID of the revision.

    Returns:
        A BytesIO object containing the file data, and the MIME type if available.
    """
    request = drive_service.revisions().get_media(
        fileId=file_id, revisionId=revision_id
    )
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    buffer.seek(0)

    # Optionally, get MIME type for download_button
    revision_metadata = (
        drive_service.revisions()
        .get(fileId=file_id, revisionId=revision_id)
        .execute()
    )
    mime_type = revision_metadata.get("mimeType", "application/octet-stream")

    return buffer, mime_type


def gds_restore_file(drive_service, file_id):
    """
    Restores a file from a shared Google Drive by removing it from the trash.

    Args:
        drive_service: The authenticated Google Drive service object.
        file_id (str): The ID of the file to restore.

    Returns:
        dict: The restored file's metadata, or None if the operation fails.
    """
    try:
        # Restore the file by updating its 'trashed' status to False
        file = (
            drive_service.files()
            .update(
                fileId=file_id,
                body={"trashed": False},
                supportsAllDrives=True,
                fields="id, name, mimeType, trashed",
            )
            .execute()
        )

        print(f"File '{file['name']}' (ID: {file['id']}) has been restored.")
        return True

    except Exception as e:
        print(f"An error occurred while restoring the file: {e}")
        return False


def gds_delete_file(drive_service, file_id, delete_permanently=False):
    """
    Deletes a file from Google Drive or moves it to trash based on user preference.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_id: ID of the file to delete.
        delete_permamently: Boolean flag to permanently delete the file.
    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    try:
        if delete_permanently:
            print("Permanently deleting file...")
            drive_service.files().delete(
                fileId=file_id, supportsAllDrives=True
            ).execute()

        else:
            print("Moving file to trash...")
            drive_service.files().update(
                fileId=file_id, body={"trashed": True}, supportsAllDrives=True
            ).execute()

        return True

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return False


def gds_delete_version(drive_service, file_id, version_id):
    """
    Deletes a specific version of a file on Google Drive.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_id (str): The ID of the file.
        version_id (str): The ID of the version to delete.

    Returns:
        bool: True if the version was successfully deleted, False otherwise.
    """
    print("Deleting version...")
    try:
        # Delete the specific version
        drive_service.revisions().delete(
            fileId=file_id,
            revisionId=version_id,
        ).execute()

        print(f"Version {version_id} of file {file_id} deleted successfully.")
        return True

    except Exception as e:
        print(
            f"An error occurred while deleting version {version_id} of file {file_id}: {e}"
        )
        return False


def gds_get_subfolders_hierarchical(
    drive_service,
    drive_id,
    max_depth=None,
    search_term="",
    fields="id, name",
    folder_id=None,  # New argument for folder ID
):
    """
    Recursively fetches project folders up to a specified depth in the hierarchy, maintaining the original hierarchy order,
    and optionally filtering by a search term. If a folder_id is provided, starts searching from that folder.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        drive_id (str): The ID of the shared drive.
        max_depth (int or None): Maximum depth to search for folders. If None, will go on indefinitely.
        search_term (str): Term to search for in the folder names (optional).
        fields (str): Fields to retrieve for each folder.
        folder_id (str or None): The ID of the folder to start searching from. If None, search starts from the root.

    Returns:
        list: A list of dictionaries containing folder information of the subfolders (id, name, modifiedTime, createdTime, depth).
    """
    print("Fetching subfolders...")

    def _get_folders_recursive(parent_id, current_depth):
        """
        Helper function to recursively fetch folders.
        """
        if max_depth is not None and current_depth > max_depth:
            return []

        # Query to fetch folders under the current parent with the search term
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if search_term:
            query += f" and name contains '{search_term}'"

        results = (
            drive_service.files()
            .list(
                q=query,
                pageSize=1000,
                spaces="drive",
                fields=f"files({fields})",
                orderBy=None,  # No sorting to maintain original order
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=drive_id,
            )
            .execute()
        )

        folders = results.get("files", [])
        all_folders = []

        for folder in folders:
            # Add the current folder with its depth
            folder_with_depth = {**folder, "depth": current_depth}
            all_folders.append(folder_with_depth)

            # Recursively fetch subfolders if max_depth is not reached
            subfolders = _get_folders_recursive(
                folder["id"], current_depth + 1
            )
            all_folders.extend(subfolders)

        return all_folders

    # If a folder_id is provided, start recursion from that folder, else from the root of the drive
    starting_folder_id = folder_id if folder_id else drive_id
    return _get_folders_recursive(starting_folder_id, 1)


def gds_rename_file(service, file_id, new_name):
    """
    Rename a file in Google Drive.

    :param service: Authenticated Google Drive API service instance.
    :param file_id: ID of the file to rename.
    :param new_name: New name for the file.
    :return: Updated file metadata if successful, None otherwise.
    """
    print("Renaming file...")
    try:
        # Prepare the update request
        file_metadata = {"name": new_name}

        # Execute the request
        updated_file = (
            service.files()
            .update(
                fileId=file_id,
                body=file_metadata,
                fields="id, name",
                supportsAllDrives=True,
            )
            .execute()
        )
        return updated_file

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def gds_get_current_version(
    service, file_id, fields="revisions(id, originalFilename)"
):
    """
    Get the most recent version of a file
    given its file_id using Google Drive API.

    :param service: Authenticated Google Drive API service instance.
    :param file_id: The ID of the file to retrieve the latest version for.
    :param fields: The fields to include in the response.
                     Default is "revisions(id, originalFilename)".

    :return: The latest revision dictionary or None if no revisions found.

    """
    print(f"Fetching current version for file with ID: {file_id}")
    try:
        revisions = (
            service.revisions()
            .list(
                fileId=file_id,
                fields=fields,
            )
            .execute()
        )

        if not revisions:
            print("No revisions found for file with ID: {file_id}")
            return None

        return revisions["revisions"][-1]

    except Exception as error:
        st.error(f"An error occurred: {error}")
        print(f"An error occurred: {error}")
        return None


def gds_get_versions_of_a_file(
    service, file_id, fields="id, modifiedTime, originalFilename"
):
    """
    Retrieves the versions of a file from a shared Google Drive.

    :param service: The Google Drive API service object.
    :param file_id: The ID of the file to retrieve versions for.
    :param fields: The fields to include in the response.
                   Default is "id, modifiedTime, originalFilename".
    :return: A list of file version dictionaries containing the specified
             fields.
    """
    print("Fetching versions of selected file...")
    try:
        # Get the list of revisions (versions) for the file
        revisions = (
            service.revisions()
            .list(
                fileId=file_id,
                fields=f"revisions({fields})",
            )
            .execute()
        )

        # Extract the revisions from the response
        return revisions.get("revisions", [])

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return []


def gds_get_version_info(
    service,
    file_id,
    version_id,
    fields="id, originalFilename",
):
    """
    Get a specific version of a file from Google Drive.

    :param service: Authenticated Google Drive API service instance.
    :param file_id: ID of the file to retrieve the version for.
    :param version_id: ID of the version to retrieve.
    :param fields: Fields to include in the response.

    :return: A dictionary containing version metadata or None if not found.
    """
    print(f"Fetching version {version_id} for file {file_id}...")
    try:
        revision = (
            service.revisions()
            .get(fileId=file_id, revisionId=version_id, fields=fields)
            .execute()
        )

        return revision

    except HttpError as error:
        st.error(f"An error occurred: {error}")
        print(f"An error occurred: {error}")
        return None


def gds_get_file_info_shared_drive(
    service, file_id, fields="id, name, size, mimeType"
):
    """
    Retrieves specified fields of a file from a shared Google Drive.

    :param service: The Google Drive API service object.
    :param file_id: The ID of the file to retrieve information for.
    :param fields: The fields to include in the response.
                   Default is "id, name, size, mimeType".

    :return: A dictionary containing the specified fields of the file.
    """
    print("Fetching file information...")
    try:
        # Use the Google Drive API to get file information
        file_info = (
            service.files()
            .get(
                fileId=file_id,
                fields=fields,
                supportsAllDrives=True,
            )
            .execute()
        )

        return file_info

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return None


def get_folders_hierarchy(service, drive_id):
    """
    Fetches the folder hierarchy of a shared Google Drive
    and organizes it into a nested dictionary structure.

    :param service: Authenticated Google Drive API service instance.
    :param drive_id: ID of the shared Google Drive.

    :return: A nested dictionary representing the folder hierarchy.
    """
    print("Fetching folder hierarchy...")
    query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
    folders = {}  # Stores all folders by ID
    hierarchy = {}

    page_token = None
    while True:
        results = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                corpora="drive",
                driveId=drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields="nextPageToken, files(id, name, parents)",
                pageToken=page_token,
            )
            .execute()
        )

        for file in results.get("files", []):
            folders[file["id"]] = {
                "id": file["id"],  # Ensure every folder keeps its ID
                "name": file["name"],
                "parents": file.get("parents", []),
                "children": [],  # Prepare a placeholder for child nodes
            }

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    for folder_id, folder_data in folders.items():
        parent_ids = folder_data["parents"]
        if not parent_ids or drive_id in parent_ids:  # It's a root folder
            hierarchy[folder_id] = folder_data
        else:
            for parent_id in parent_ids:
                if parent_id in folders:
                    folders[parent_id]["children"].append(folder_data)

    return hierarchy


def gds_upload_file(
    drive_service,
    file_path,
    folder_id=None,
    description=None,
    fields="id",
):
    """
    Uploads a file to a shared Google Drive.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_path: Path to the file to upload.
        folder_id: ID of the folder to upload the file to.
        description: Description of the file.
        fields: Fields to include in the response.

    Returns:
        The uploaded file metadata or None if an error occurs.

    """
    print("Uploading file...")
    try:
        # Check if the file is a stream or a local file
        if hasattr(file_path, "name"):
            file_name = file_path.name
            mime_type = file_path.type
            media = MediaIoBaseUpload(file_path, mimetype=mime_type)

        else:
            file_name = file_path.split("/")[-1]
            mime_type, _ = mimetypes.guess_type(file_name)
            if not mime_type:
                mime_type = "application/octet-stream"
            media = MediaFileUpload(
                file_path, resumable=True, mimetype=mime_type
            )

        # Define file metadata
        file_metadata = {
            "name": file_name,
        }

        # Set the folder ID and description if provided
        if folder_id:
            file_metadata["parents"] = [folder_id]
        if description:
            file_metadata["description"] = description

        # Upload the file
        request = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields=fields,
        )
        uploaded_file = request.execute()

        return uploaded_file

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def gds_get_files(
    service,
    drive_id,
    search_term=None,
    trashed=False,
    fields="id, name",
    folder_id=None,
):
    """
    Retrieve files from a shared Google Drive based on search criteria,
    excluding folders and shortcuts. If folder_id is provided, it will
    search for files within that folder and all its subfolders.

    :param service: Authenticated Google Drive API service instance.
    :param drive_id: ID of the shared drive.
    :param search_term: Optional search term to filter files by name.
    :param trashed: Boolean to include or exclude trashed files.
    :param fields: Fields to include in the response.
    :param folder_id: Optional folder ID to search for files starting from this folder and its subfolders.
    :return: List of files matching the criteria.
    """
    print("Fetching files...")
    try:
        # Base query to exclude folders and shortcuts
        # Also exclude Google Docs, Sheets, and Slides files cause these have
        # their own versioning system inside google drive
        query = (
            f"trashed={str(trashed).lower()} "
            f"and mimeType != 'application/vnd.google-apps.folder' "
            f"and mimeType != 'application/vnd.google-apps.shortcut' "
            f"and mimeType != 'application/vnd.google-apps.document' "
            f"and mimeType != 'application/vnd.google-apps.spreadsheet' "
            f"and mimeType != 'application/vnd.google-apps.presentation'"
        )

        # Add search term to the query if provided
        if search_term:
            query += f" and name contains '{search_term}'"

        # If folder_id is provided, search within the folder and its subfolders
        if folder_id:
            # Get all subfolder IDs (including the root folder_id)
            folder_ids = _get_all_subfolder_ids(service, folder_id)
            # Construct query to search in all folders
            query += (
                " and ("
                + " or ".join(f"'{fid}' in parents" for fid in folder_ids)
                + ")"
            )

        # Execute the query
        results = (
            service.files()
            .list(
                q=query,
                corpora="drive",
                driveId=drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields=f"files({fields})",
            )
            .execute()
        )

        # Return the list of files
        files = results.get("files", [])
        return files

    except HttpError as error:
        st.error(f"An error occurred: {error}")
        print(f"An error occurred: {error}")
        return []


def gds_download_version_image(service, file_id, revision_id):
    """Download the actual content of a specific version/revision of a file"""
    try:
        print("Fetching version content...")
        # Get the revision metadata first
        revision = (
            service.revisions()
            .get(
                fileId=file_id,
                revisionId=revision_id,
                fields="exportLinks, mimeType",
            )
            .execute()
        )

        # Check if this is an image we can download directly
        if revision.get("mimeType", "").startswith("image/"):
            # For images, we can use get_media directly
            request = service.revisions().get_media(
                fileId=file_id, revisionId=revision_id
            )
            return request.execute()
        else:
            # For other file types that might need export
            export_links = revision.get("exportLinks", {})
            if export_links:
                # Choose an appropriate export format
                # For images, you might want to use the original download URL
                download_url = (
                    export_links.get("image/jpeg")
                    or export_links.get("image/png")
                    or export_links.get("application/octet-stream")
                )
                if download_url:
                    response = service._http.request(download_url)
                    if response[0].status == 200:
                        return response[1]

        st.error("Unable to download the version content")
        return None

    except Exception as e:
        st.error(f"An error downloading version: {e}")
        print(f"An error downloading version: {e}")
        return None


def gds_get_folders_info(service, folder_ids, fields="id, name"):
    """
    Fetches the name and id for each folder ID provided, including those in shared drives.

    Args:
        service: Authorized Google Drive API service instance.
        folder_ids: List of folder IDs to look up.
        fields: Comma-separated string of fields to return.

    Returns:
        List of dicts with 'id' and 'name' of each folder.
    """
    print("Fetching folder information...")
    folders = []

    for folder_id in folder_ids:
        try:
            folder = (
                service.files()
                .get(
                    fileId=folder_id,
                    fields=fields,
                    supportsAllDrives=True,
                )
                .execute()
            )
            folders.append({"id": folder["id"], "name": folder["name"]})
        except Exception as e:
            print(f"Error fetching folder {folder_id}: {e}")

    return folders


def gds_move_file(drive_service, file_id, current_parent_id, new_parent_id):
    """
    Moves a file to a different folder in Google Drive, including Shared Drives.

    Args:
        drive_service: Authenticated Google Drive API service object.
        file_id: ID of the file to move.
        current_parent_id: ID of the folder the file is currently in.
        new_parent_id: ID of the folder to move the file to.

    Returns:
        The updated file metadata.
    """
    print("Moving file...")
    try:
        # Move the file to the new folder
        updated_file = (
            drive_service.files()
            .update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=current_parent_id,
                supportsAllDrives=True,  # Required for Shared Drives
                fields="id, name, parents",
            )
            .execute()
        )

        return updated_file

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return None


def _get_all_subfolder_ids(service, folder_id, drive_id=None):
    """
    Recursively retrieves all subfolder IDs starting from a given folder ID.

    :param service: Authenticated Google Drive API service instance.
    :param folder_id: ID of the folder to start searching from.
    :param drive_id: ID of the shared drive (required if corpora="drive").
    :return: List of folder IDs (including the root folder_id).
    """
    print("Fetching all subfolder IDs...")
    folder_ids = [folder_id]  # Start with the root folder
    stack = [folder_id]  # Use a stack for DFS (Depth-First Search)

    while stack:
        current_folder_id = stack.pop()
        # Query to find all subfolders in the current folder
        query = (
            f"'{current_folder_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        # Prepare the API request
        request = service.files().list(
            q=query,
            corpora="drive" if drive_id else "allDrives",
            driveId=drive_id if drive_id else None,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields="files(id)",
        )
        # Execute the request
        results = request.execute()
        subfolders = results.get("files", [])
        for subfolder in subfolders:
            folder_ids.append(subfolder["id"])  # Add subfolder ID to the list
            stack.append(
                subfolder["id"]
            )  # Add subfolder ID to the stack for further traversal

    return folder_ids


class DriveModel:
    def __init__(self, drive_service):
        self.drive_service = drive_service

    def drive_exists(self, drive_id):
        """Check if a specific drive exists and is accessible."""
        try:
            # Attempt to fetch the drive details
            self.drive_service.drives().get(driveId=drive_id).execute()
            return True
        except Exception as e:
            st.error(f"An error occurred: {e}")
            print(f"Error checking drive existence: {e}")
            return False


def gds_get_all_drives(drive_service):
    """
    Fetch the list of shared drives.

    Args:
        drive_service: Authenticated Google Drive API service instance.

    Returns:
        List of shared drives with their IDs and names.
    """
    print("Fetching shared drives...")
    drives = []
    page_token = None
    try:
        while True:
            # Call the Drive API to list shared drives
            response = (
                drive_service.drives()
                .list(
                    pageSize=100,
                    fields="nextPageToken, drives(id, name)",
                    pageToken=page_token,
                )
                .execute()
            )

            # Append the drives to the list
            drives.extend(response.get("drives", []))

            # Check if there are more drives to retrieve
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break
        return drives

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        return []


def gds_get_most_recent_files_recursive(
    service, drive_id, fields=("id, name"), folder_id=None, max_results=10
):
    """
    Lists the most recently modified files in the user's Google Drive, searching recursively in subfolders.
    Excluding the google workspace files.

    :param service: Authenticated Google Drive API service instance.
    :param drive_id: ID of the drive to search (use None for My Drive).
    :param fields: Fields to return for each file.
    :param folder_id: ID of the folder to search within (optional).
    :param max_results: Maximum number of files to return.
    :return: List of the most recent files with their IDs and names.
    """
    print("Fetching most recent files...")
    try:
        # List to store all files
        all_files = []

        # Function to recursively search for files
        def search_folder(folder_id):
            nonlocal all_files
            if len(all_files) >= max_results:
                return

            # Query to find files in the current folder
            # (excluding subfolders. trashed files and
            # google workspace files
            query = (
                f"'{folder_id}' in parents and "
                "mimeType != 'application/vnd.google-apps.folder' and "
                "trashed = false and "
                "mimeType != 'application/vnd.google-apps.shortcut' and "
                "mimeType != 'application/vnd.google-apps.document' and "
                "mimeType != 'application/vnd.google-apps.spreadsheet' and "
                "mimeType != 'application/vnd.google-apps.presentation'"
            )
            file_results = (
                service.files()
                .list(
                    q=query,
                    corpora="drive" if drive_id else "user",
                    driveId=drive_id if drive_id else None,
                    includeItemsFromAllDrives=bool(drive_id),
                    supportsAllDrives=bool(drive_id),
                    pageSize=max_results - len(all_files),
                    fields=f"files({fields})",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )
            files = file_results.get("files", [])
            all_files.extend(files)

            # If we haven't reached max_results, search subfolders
            if len(all_files) < max_results:
                # Query to find subfolders in the current folder
                folder_query = (
                    f"'{folder_id}' in parents and "
                    "mimeType = 'application/vnd.google-apps.folder' and "
                    "trashed = false"
                )
                folder_results = (
                    service.files()
                    .list(
                        q=folder_query,
                        corpora="drive" if drive_id else "user",
                        driveId=drive_id if drive_id else None,
                        includeItemsFromAllDrives=bool(drive_id),
                        supportsAllDrives=bool(drive_id),
                        pageSize=100,  # Adjust as needed
                        fields="files(id)",
                    )
                    .execute()
                )
                subfolders = folder_results.get("files", [])
                for subfolder in subfolders:
                    search_folder(subfolder["id"])

        # Start the recursive search
        if folder_id:
            search_folder(folder_id)
        else:
            # If no folder_id is provided, start from the root of the drive
            search_folder("root")

        # Sort all files by modifiedTime (descending) and return up to max_results
        all_files.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
        return all_files[:max_results]

    except Exception as error:
        st.error(f"An error occurred: {error}")
        print(f"An error occurred: {error}")
        return []


def gds_revert_version(
    service, file_id, file_name, revision_id, revision_name
):
    """
    Reverts a file to a specific revision by downloading the revision content
    and uploading it as the current version.

    Args:
        service: Authenticated Google Drive API service instance.
        file_id: ID of the file to revert a version for.
        file_name: Name of the file to revert a version for.
        revision_id: ID of the revision to revert to.
        revision_name: Name of the revision to revert to.
    """
    print("Reverting file version...")
    # Step 1: Set the path to the Downloads folder
    download_folder = os.path.expanduser("~/Downloads")
    file_path = os.path.join(download_folder, revision_name)

    # Step 2: Download the specific revision
    try:
        request = service.revisions().get_media(
            fileId=file_id,
            revisionId=revision_id,
        )
        file_to_download = request.execute()

        with open(file_path, "wb") as temp_file:
            temp_file.write(file_to_download)
        print(f"File downloaded to {file_path}")

    except Exception as error:
        st.error(f"An error occurred: {error}")
        print(f"An error occurred while downloading the file: {error}")
        return False

    # Step 3: Upload the downloaded file as the current version
    gds_upload_version(service, file_id, file_name, file_path)

    # Step 4: Delete the temporary downloaded file
    try:
        os.remove(file_path)
        print(f"File {file_path} deleted.")
        return True

    except Exception as error:
        print(f"An error occurred while deleting the file locally: {error}")
        return False


def gds_upload_version(
    drive_service,
    file_id,
    file_name,
    file_path,
    change_file_type=False,
    keep_forever=False,
    current_mime_type=None,
):
    """
    Uploads a new version of an existing file in Google Drive.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_id: ID of the file to upload a new version for.
        file_name: Name of the file to upload a new version for.
        file_path: Path to the file to upload as a new version.
        change_file_type: Boolean flag to change the file type.
        keep_forever: Boolean flag to keep the file forever.
        current_mime_type: The current MIME type of the file.
    Returns:
        The updated file's metadata or None if an error occurs.
    """
    # google api uploading versions doesnt allow to store the original
    # filename of the file you want to upload, but instea looks at the
    # name of the file in google drive and sets that as the name of the version
    # so we need to change the name of the file in google drive before upload
    # and revert it back after upload
    print("Uploading new version...")
    print("keep forever", keep_forever)
    try:
        if hasattr(file_path, "name"):
            version_name = file_path.name
            new_mime_type = file_path.type
            media = MediaIoBaseUpload(file_path, mimetype=new_mime_type)

        else:
            version_name = os.path.basename(file_path)
            new_mime_type, _ = mimetypes.guess_type(version_name)
            if not new_mime_type:
                new_mime_type = "application/octet-stream"
            media = MediaFileUpload(
                file_path, resumable=True, mimetype=new_mime_type
            )

        # Step 1: change name on google drive
        gds_rename_file(drive_service, file_id, version_name)

        file_metadata = {"name": version_name}

        if change_file_type:
            file_metadata["mimeType"] = new_mime_type
        else:
            if current_mime_type:
                file_metadata["mimeType"] = current_mime_type
        # Step 2: upload the new version to google drive
        request = drive_service.files().update(
            fileId=file_id,
            body=file_metadata,
            media_body=media,
            fields="id, name",
            supportsAllDrives=True,
        )

        uploaded_version = request.execute()

        # Step 3: set the version to keep forever
        if keep_forever:
            latest_version = gds_get_current_version(drive_service, file_id)
            latest_version_id = latest_version["id"]
            gds_update_keep_forever_version(
                drive_service, file_id, latest_version_id, keep_forever=True
            )
            print(f"Version {latest_version_id} will be kept forever.")

        # Step 4: revert the name of the file back to the original
        gds_rename_file(drive_service, file_id, file_name)

        print(
            f"New version {version_name} uploaded successfully for file ID: "
            f"{file_id}"
        )
        return uploaded_version

    except Exception as error:
        print(f"An error occurred: {error}")
        return None


def gds_update_keep_forever_version(
    drive_service, file_id, revision_id, keep_forever=True
):
    """
    Updates the 'keepForever' status of a specific version of a file in Google Drive.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_id: ID of the file to update the version for.
        revision_id: ID of the revision to update.
        keep_forever: Boolean flag to set the version to keep forever.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        drive_service.revisions().update(
            fileId=file_id,
            revisionId=revision_id,
            body={"keepForever": keep_forever},
        ).execute()

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def gds_delete_old_versions(drive_service, file_id):
    """ "
    Deletes all previous versions of a file in Google Drive."
    And keeps the most recent version.

    Args:
        drive_service: Authenticated Google Drive API service instance.
        file_id: ID of the file to delete old versions for.

    """

    revisions = gds_get_versions_of_a_file(drive_service, file_id, fields="id")

    if not revisions:
        print("No previous versions found.")
        return

    current_revision_id = revisions[-1]["id"]
    for revision in revisions:
        revision_id = revision["id"]
        if revision_id != current_revision_id:
            try:
                drive_service.revisions().delete(
                    fileId=file_id, revisionId=revision_id
                ).execute()
                print(f"Deleted revision {revision_id}")
            except Exception as e:
                print(f"Error deleting revision {revision_id}: {e}")
