import streamlit as st
from views.version_control_ui import VersionControlUI
from handlers.version_control_handler import VersionControlHandler


class VersionControlController:
    def __init__(
        self,
        drive_service,
        user_name,
        border=True,
    ):
        """
        Initializes the Version Control Controller with the necessary services.

        Args:
            drive_service: The Google Drive service instance.
            user_name (str): The name of the user.
            border (bool): Whether to display borders in the UI.
        """
        self.border = border

        self.ui = VersionControlUI()
        self.handler = VersionControlHandler(
            drive_service,
            user_name,
        )

    def _initialize_session_state(self):
        """
        Initializes all required session state variables with default values.
        """
        defaults = {
            # Core selection states
            "search_term_files": None,
            "selected_file": None,
            "selected_version": None,
            # Batch operation states
            "batch_selected_files": [],
            "batch_selected_versions": [],
            # UI reset keys
            "files_reset_key": 0,
            "versions_reset_key": 0,
            # Cache-related states
            "files_for_display": [],
        }

        for key, value in defaults.items():
            st.session_state.setdefault(key, value)

    def start(self):
        """
        Runs the application by connecting the UI and Handler.
        """
        self._initialize_session_state()

        st.title("Version Control", anchor="False")

        # Create a container for the main content
        main_container = st.container()

        with main_container:
            # Create columns for files and versions
            col_tbl_files, col_tbl_versions = st.columns(2, gap="large")

            # Create containers for each column to control height
            with col_tbl_files:
                files_container = st.container(border=self.border)
                with files_container:
                    self._handle_and_display_files()

            with col_tbl_versions:
                versions_container = st.container(border=self.border)
                with versions_container:
                    self._handle_and_display_versions()

            # Create a spacer to ensure consistent height
            if not st.session_state.get("selected_file"):
                st.write("")  # Empty space to maintain layout

            # Create action buttons row
            actions_row = st.columns(2, gap="large")

            with actions_row[0]:
                files_actions_container = st.container(border=self.border)
                with files_actions_container:
                    # Upload new file(s)
                    if self.ui.display_button(
                        key="upload_file",
                        label=":material/upload_file: Upload File(s)",
                        use_container_width=True,
                        help="Upload new file(s) to the selected folder",
                    ):
                        self._handle_file_upload()

                    if self.ui.display_button(
                        key="create_folder",
                        label=":material/create_new_folder: Create Folder",
                        use_container_width=True,
                        help="Create a new folder",
                    ):
                        self._handle_folder_creation()

            with actions_row[1]:
                versions_actions_container = st.container(border=self.border)
                with versions_actions_container:
                    # Only show version actions if a file is selected
                    if st.session_state.get("selected_file"):
                        # Upload new version(s)
                        if self.ui.display_button(
                            key="upload_version",
                            label=":material/upload: Upload new version(s)",
                            use_container_width=True,
                            help="Upload new version(s) for the selected file",
                        ):
                            self._handle_version_upload()

                        if self.ui.display_button(
                            key="revert_version",
                            label=":material/history: Revert to version",
                            use_container_width=True,
                            help="Revert the selected file to a previous version",
                        ):
                            self._handle_version_revert()
                    else:
                        st.write("Select a file to enable version actions")
                        st.write("")  # Maintain space

            self._display_batch_actions()

    def _display_batch_actions(self):
        """
        Displays action buttons and input fields for batch operations.
        """
        col_actions_files, col_actions_versions = st.columns(
            2, border=self.border
        )

        with col_actions_files:
            self._handle_batch_selection_files()

            if self.ui.display_button(
                key="move_file",
                label=":material/drive_file_move: Move File(s)",
                use_container_width=True,
                help="Move selected file(s) to another folder",
            ):
                self._handle_file_move()

            if self.ui.display_button(
                key="rename_file",
                label=":material/edit: Rename File(s)",
                use_container_width=True,
                help="Rename selected file(s)",
            ):
                self._handle_file_rename()

            if self.ui.display_button(
                key="delete_file",
                label=":material/delete: Delete File(s)",
                use_container_width=True,
                help="Delete selected file(s)",
            ):
                self._handle_file_deletion()

            if self.ui.display_button(
                key="restore_file",
                label=":material/restore: Restore File(s)",
                use_container_width=True,
                help="Restore selected file(s) from trash",
            ):
                self._handle_file_restore()

        with col_actions_versions:
            self._handle_batch_selection_versions()

            if self.ui.display_button(
                key="delete_version",
                label=":material/delete: Delete Version(s)",
                use_container_width=True,
                help="Delete selected version(s)",
            ):
                self._handle_version_deletion()

            if self.ui.display_button(
                key="toggle_keep_forever",
                label=":material/lock_clock: Toggle Keep Forever",
                use_container_width=True,
                help="Check/uncheck Keep Forever status for selected versions",
            ):
                self._handle_toggle_keep_forever()

            if self.ui.display_button(
                key="prepare_download",
                label=":material/download: Download Version(s)",
                use_container_width=True,
                help="Download selected version(s) as a zip file",
            ):
                self._handle_prepare_download()

    def _handle_and_display_files(self):
        """
        Handles the retrieval and display of files.

        Args:
            None

        Returns:
            None
        """
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]
        search_term = st.session_state.search_term_files or None
        cache_key = f"files_{drive_id}_{project_folder_id}_{search_term}"

        self.ui.display_title("Files")
        # Update search_term_files in session
        # state immediately when search changes
        new_search_term = self.ui.display_search()

        if new_search_term != st.session_state.search_term_files:
            st.session_state.search_term_files = new_search_term

            if cache_key in st.session_state:
                del st.session_state[cache_key]
            # Rerun to apply the new search immediately
            st.rerun()

        if self.ui.display_button(
            key="refresh_files",
            label=":material/refresh:",
            help="Refresh files",
        ):
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()

        if cache_key not in st.session_state:
            with st.spinner("Searching for files..."):
                # Use gds_get_most_recent_files_recursive if no search term
                if not search_term:
                    files_from_gd = self.handler.get_most_recent_files(
                        drive_id,
                        project_folder_id,
                        max_results=20,
                        fields="id, name, mimeType, createdTime, modifiedTime, size, webViewLink, webContentLink, description, parents",
                    )
                else:
                    # Fall back to full search when a term is provided
                    files_from_gd = self.handler.get_files_from_folder(
                        drive_id,
                        project_folder_id,
                        search_term,
                        fields="id, name, mimeType, createdTime, modifiedTime, size, webViewLink, webContentLink, description, parents",
                    )

                folder_ids = list(
                    {
                        parent
                        for file in files_from_gd
                        for parent in file.get("parents", [])
                        if parent is not None
                    }
                )
                folder_info = self.handler.get_folders_info(
                    folder_ids, fields="id, name"
                )
                files_for_display = self.handler.format_files_for_display(
                    files_from_gd, folder_info
                )

                # Save in session state
                st.session_state[cache_key] = files_for_display
        else:
            files_for_display = st.session_state[cache_key]

        reset_key = st.session_state.get("files_reset_key", 0)
        # Display the single-select grid
        selected_file = self.ui.display_dataframe(
            files_for_display,
            key=f"files_table_{reset_key}",
            height=300,
            is_versions=False,
        )

        st.session_state.selected_file = selected_file
        st.session_state.files_for_display = files_for_display

    def _handle_and_display_versions(self):
        """
        Retrieves and displays file versions.

        Args:
            None

        Returns:
            None
        """
        selected_file = st.session_state.get("selected_file")
        selected_file_id = selected_file.get("id") if selected_file else None
        selected_file_name = (
            selected_file.get("name") if selected_file else None
        )
        self.ui.display_title("Versions")

        if not selected_file_id:
            st.write("Please select a file to view its versions")
            return None
        else:
            st.write(f"##### for file with name '{selected_file_name}'")
        # Cache key based on selected file
        cache_key = f"versions_for_file_{selected_file_id}"
        if self.ui.display_button(
            key="refresh_versions",
            label=":material/refresh:",
            help="Refresh versions",
        ):
            if cache_key in st.session_state:
                del st.session_state[cache_key]

        if cache_key in st.session_state:
            versions_for_display = st.session_state[cache_key]
        else:
            with st.spinner("Searching for versions..."):
                versions_for_display = (
                    self.handler.get_versions_of_file_for_display(
                        selected_file_id
                    )
                )
                st.session_state[cache_key] = versions_for_display

        if not versions_for_display:
            st.write("No versions found for the selected file")
            return None

        reset_key = st.session_state.get("versions_reset_key", 0)
        selected_version = self.ui.display_dataframe(
            versions_for_display,
            key=f"versions_table_{reset_key}",
            height=380,
            is_versions=True,
        )
        st.session_state.selected_version = selected_version

    def _handle_batch_selection_files(self):
        """
        Handles the batch selection of files.

        Args:
            None

        Returns:
            None
        """
        st.write("### Batch Operations")
        files_for_display = st.session_state.get("files_for_display", [])
        batch_selected_files = self.ui.display_file_multi_select(
            files_for_display, key="batch_files"
        )
        st.session_state.batch_selected_files = batch_selected_files

    def _handle_batch_selection_versions(self):
        """
        Handles the batch selection of versions
        and stores them in session state.

        Args:
            None

        Returns:
            None
        """
        st.write("### Batch Version Operations")
        selected_file = st.session_state.get("selected_file")

        if selected_file:
            cache_key = f"versions_for_file_{selected_file['id']}"
            versions_for_display = st.session_state.get(cache_key, [])

            batch_selected_versions = self.ui.display_version_multi_select(
                versions_for_display,
                key="batch_versions",
                disabled=False,
            )
            st.session_state.batch_selected_versions = batch_selected_versions
        else:
            # Still render the selection UI,
            # but disable it with a helpful message
            self.ui.display_version_multi_select(
                [],
                key="batch_versions_disabled",
                disabled=True,
                placeholder="Select a file to enable version batch operations",
            )

    def _handle_file_upload(self):
        """
        Handles the file upload process.

        Args:
            None

        Returns:
            None
        """
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]

        subfolders = self.handler.get_subfolders_hierarchically(
            drive_id, project_folder_id
        )

        # Add the project folder to the list of folders to display at the top
        folders_to_display = [
            st.session_state.selected_project_folder
        ] + subfolders

        try:

            def on_upload_callback(
                selected_folder, files_to_upload, description
            ):
                for file_to_upload in files_to_upload:
                    with st.spinner(
                        f"Uploading file {file_to_upload.name}..."
                    ):
                        success, message = self.handler.upload_file(
                            file_to_upload,
                            selected_folder,
                            description,
                        )
                    self.ui.display_feedback_message(success, message)

                    self._clear_files_session_state()

            self.ui.display_upload_new_file_dialog(
                folders_to_display, on_upload_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while uploading the file: {str(e)}",
            )

    def _handle_folder_creation(self):
        """Handles the folder creation process."""
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]

        subfolders = self.handler.get_subfolders_hierarchically(
            drive_id, project_folder_id
        )

        # Add the project folder to the list of folders to display at the top
        folders_to_display = [
            st.session_state.selected_project_folder
        ] + subfolders

        try:

            def on_create_callback(folder_name, parent_folder):
                with st.spinner(f"Creating folder '{folder_name}'..."):
                    success, message = self.handler.create_folder(
                        folder_name,
                        parent_folder["id"],
                    )
                self.ui.display_feedback_message(success, message)

            self.ui.display_create_folder_dialog(
                folders_to_display, on_create_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False, f"An error occurred while creating folder: {str(e)}"
            )

    def _handle_version_upload(self):
        """
        Handles the version upload process.

        Args:
            None

        Returns:
            None
        """
        selected_file = (
            st.session_state.selected_file
            if st.session_state.selected_file
            else None
        )
        if not selected_file:
            st.warning("Please select a file to upload new versions for.")
            return
        try:

            def on_upload_callback(
                selected_file,
                files_to_upload,
                description,
                keep_forever,
                change_file_type,
                keep_only_latest_version,
            ):
                for file in files_to_upload:
                    # Add a spinner to show while uploading
                    with st.spinner(
                        f"Uploading new version with name {file.name}..."
                    ):
                        success, message = self.handler.upload_version(
                            selected_file,
                            file,
                            description,
                            keep_forever,
                            change_file_type,
                            keep_only_latest_version,
                        )

                    self.ui.display_feedback_message(success, message)
                    self._clear_versions_session_state()

            self.ui.display_upload_new_version_dialog(
                selected_file, on_upload_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while uploading a new version: {str(e)}",
            )

    def _handle_version_revert(self):
        """
        Handles the version revert process.

        Args:
            None

        Returns:
            None
        """
        selected_file = (
            st.session_state.selected_file
            if st.session_state.selected_file
            else None
        )
        selected_version = (
            st.session_state.selected_version
            if st.session_state.selected_version
            else None
        )
        if not selected_file:
            st.warning("Please select a file to revert a version for.")
            return
        if not selected_version:
            st.warning("Please select a version to revert to.")
            return

        try:

            def on_revert_callback(
                selected_file, selected_version, description
            ):
                with st.spinner("Reverting version..."):
                    success, message = self.handler.revert_version(
                        selected_file, selected_version, description
                    )
                self.ui.display_feedback_message(success, message)
                self._clear_versions_session_state()

            self.ui.display_revert_version_dialog(
                selected_file, selected_version, on_revert_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False, f"An error occurred when reverting a version: {str(e)}"
            )

    def _handle_file_deletion(self):
        """
        Handles the file deletion process for single or multiple files.

        Args:
            None

        Returns:
            None
        """
        # Check for batch selected files first
        batch_selected_files = st.session_state.get("batch_selected_files", [])

        # Fall back to single selection if no batch selection
        if not batch_selected_files:
            selected_file = st.session_state.get("selected_file")
            if not selected_file:
                st.warning("Please select file(s) to delete.")
                return
            batch_selected_files = [selected_file]

        try:

            def on_delete_callback(selected_file, delete_permanently):
                with st.spinner(f"Deleting file {selected_file['name']}..."):
                    success, message = self.handler.delete_file(
                        selected_file["id"], delete_permanently
                    )
                self.ui.display_feedback_message(success, message)
                self._clear_files_session_state()

            self.ui.display_delete_file_dialog(
                batch_selected_files, on_delete_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while deleting the file(s): {str(e)}",
            )

    def _handle_file_restore(self):
        """
        Handles the file restore process for single or multiple files.

        Args:
            None

        Returns:
            None
        """
        drive_id = st.session_state.selected_drive["id"]

        trashed_files = self.handler.get_files_from_trash(drive_id)

        folder_ids = list(
            {
                parent
                for file in trashed_files
                for parent in file.get("parents", [])
                if parent is not None
            }
        )
        folder_info = self.handler.get_folders_info(
            folder_ids, fields="id, name"
        )

        trashed_files_with_folder = self.handler.format_files_for_display(
            trashed_files, folder_info
        )

        # Sort files by modified time in descending order
        trashed_files_with_folder.sort(
            key=lambda x: x["modifiedTime"], reverse=True
        )

        try:

            def on_restore_callback(selected_files):
                success_count = 0
                for file in selected_files:
                    with st.spinner(f"Restoring file {file['name']}..."):
                        success, message = self.handler.restore_file(
                            file["id"]
                        )
                        if success:
                            success_count += 1
                        else:
                            self.ui.display_feedback_message(success, message)

                self.ui.display_feedback_message(
                    True if success_count == len(selected_files) else False,
                    f"Restored {success_count} of "
                    f"{len(selected_files)} files.",
                )
                self._clear_files_session_state()

            self.ui.display_restore_file_dialog(
                trashed_files_with_folder, on_restore_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while restoring the file(s): {str(e)}",
            )

    def _handle_file_move(self):
        """
        Handles the file move process for single or multiple files.

        Args:
            None

        Returns:
            None
        """
        # Check for batch selected files first
        batch_selected_files = st.session_state.get("batch_selected_files", [])

        # Fall back to single selection if no batch selection
        if not batch_selected_files:
            selected_file = st.session_state.get("selected_file")
            if not selected_file:
                st.warning("Please select file(s) to move.")
                return
            batch_selected_files = [selected_file]

        # Get the list of folders
        drive_id = st.session_state.selected_drive["id"]
        project_folder_id = st.session_state.selected_project_folder["id"]
        subfolders = self.handler.get_subfolders_hierarchically(
            drive_id, project_folder_id
        )

        # Add the project folder to the list of folders to display at the top
        folders_to_display = [
            st.session_state.selected_project_folder
        ] + subfolders

        try:

            def on_move_callback(selected_files, selected_folder):
                success_count = 0
                for file in selected_files:
                    with st.spinner(f"Moving file {file['name']}..."):
                        new_folder_id = selected_folder["id"]
                        success, message = self.handler.move_file(
                            file["id"],
                            file["folder_id"],
                            new_folder_id,
                        )
                        if success:
                            success_count += 1
                        else:
                            self.ui.display_feedback_message(success, message)

                self.ui.display_feedback_message(
                    True if success_count == len(selected_files) else False,
                    f"Moved {success_count} of {len(selected_files)} files.",
                )
                self._clear_files_session_state()

            self.ui.display_move_file_dialog(
                batch_selected_files, folders_to_display, on_move_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while moving files: {str(e)}",
            )

    def _handle_version_deletion(self):
        """
        Handles the version deletion process for single or multiple versions.

        Args:
            None

        Returns:
            None
        """
        selected_file = (
            st.session_state.selected_file
            if st.session_state.selected_file
            else None
        )

        if not selected_file:
            st.warning("Please select a file to delete versions for.")
            return

        # Check for batch selected versions first
        batch_selected_versions = st.session_state.get(
            "batch_selected_versions", []
        )

        # Fall back to single selection if no batch selection
        if not batch_selected_versions:
            selected_version = st.session_state.get("selected_version")
            if not selected_version:
                st.warning("Please select version(s) to delete.")
                return
            batch_selected_versions = [selected_version]

        try:

            def on_delete_callback(selected_versions):
                success_count = 0
                for version in selected_versions:
                    with st.spinner(
                        f"Deleting version {version['originalFilename']}..."
                    ):
                        success, message = self.handler.delete_version(
                            selected_file["id"],
                            version["id"],
                        )
                        if success:
                            success_count += 1
                        else:
                            self.ui.display_feedback_message(success, message)

                self.ui.display_feedback_message(
                    True if success_count == len(selected_versions) else False,
                    f"Deleted {success_count} of "
                    f"{len(selected_versions)} versions.",
                )
                self._clear_versions_session_state()

            self.ui.display_delete_versions_dialog(
                batch_selected_versions, on_delete_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while deleting the version(s): {str(e)}",
            )

    def _handle_prepare_download(self):
        """
        Handles downloading multiple versions as a zip file.

        Args:
            None

        Returns:
            None
        """
        # Check for batch selected versions first
        batch_selected_versions = st.session_state.get(
            "batch_selected_versions", []
        )

        # Fall back to single selection if no batch selection
        if not batch_selected_versions:
            selected_version = st.session_state.get("selected_version")
            if not selected_version:
                st.warning("Please select version(s) to download.")
                return
            batch_selected_versions = [selected_version]

        file_id = (
            st.session_state.selected_file.get("id")
            if st.session_state.selected_file
            else None
        )
        if not file_id:
            st.warning("Please select a file to download versions for.")
            return

        with st.spinner(
            f"Preparing {len(batch_selected_versions)} version(s) "
            "for download..."
        ):
            file_data_list = []
            for version in batch_selected_versions:
                version_id = version.get("id")
                if not version_id:
                    continue

                file_bytes, mime_type = self.handler.get_revision_as_bytes(
                    file_id, version_id
                )

                # Determine filename
                if version.get("originalFilename"):
                    file_name = version["originalFilename"]
                else:
                    file_name = (
                        f"v{version['versionNumber']}_"
                        f"{st.session_state.selected_file.get('name', 'file')}"
                    )

                # Append to list if file bytes are valid
                if file_bytes:
                    file_data_list.append(
                        {
                            "file_bytes": file_bytes,
                            "file_name": file_name,
                            "versionNumber": version.get("versionNumber"),
                        }
                    )

            if not file_data_list:
                st.error("No valid versions to download")
                return

            # Create zip file if multiple versions,
            # or download single file directly
            if len(file_data_list) > 1:
                zip_buffer = self.handler.create_zip_file(file_data_list)
                base_name = st.session_state.selected_file.get(
                    "name", "versions"
                )
                min_version = min(v["versionNumber"] for v in file_data_list)
                max_version = max(v["versionNumber"] for v in file_data_list)
                zip_name = f"{base_name}_v{min_version}-{max_version}.zip"

                self.ui.show_download_button_zip(
                    zip_buffer, zip_name, len(file_data_list)
                )

            else:
                file_data = file_data_list[0]
                self.ui.show_download_button_single(
                    file_data["file_bytes"], file_data["file_name"]
                )

    def _handle_file_rename(self):
        """
        Handles the file renaming process.

        Args:
            None

        Returns:
            None
        """
        # Check for batch selected files first
        batch_selected_files = st.session_state.get("batch_selected_files", [])

        # Fall back to single selection if no batch selection
        if not batch_selected_files:
            selected_file = st.session_state.get("selected_file")
            if not selected_file:
                st.warning("Please select file(s) to rename.")
                return
            batch_selected_files = [selected_file]

        try:

            def on_rename_callback(new_names):
                """Callback function to handle the rename operation."""
                success_count = 0
                for file_id, new_name in new_names.items():
                    with st.spinner(f"Renaming file to {new_name}..."):
                        success, message = self.handler.rename_file(
                            file_id, new_name
                        )
                        if success:
                            success_count += 1
                        else:
                            self.ui.display_feedback_message(success, message)

                self.ui.display_feedback_message(
                    True if success_count == len(new_names) else False,
                    f"Renamed {success_count} of {len(new_names)} files.",
                )
                self._clear_files_session_state()

            if len(batch_selected_files) > 1:
                self.ui.display_rename_files_dialog(
                    batch_selected_files, on_rename_callback
                )
            else:
                self.ui.display_rename_file_dialog(
                    batch_selected_files[0],
                    lambda file, name: on_rename_callback({file["id"]: name}),
                )

        except Exception as e:
            self.ui.display_feedback_message(
                False,
                f"An error occurred while renaming files: {str(e)}",
            )

    def _handle_toggle_keep_forever(self):
        """
        Handles toggling the keepForever status for selected versions.

        Args:
            None

        Returns:
            None
        """
        selected_file = st.session_state.get("selected_file")
        if not selected_file:
            st.warning("Please select a file first.")
            return

        batch_selected_versions = st.session_state.get(
            "batch_selected_versions", []
        )
        if not batch_selected_versions:
            selected_version = st.session_state.get("selected_version")
            if not selected_version:
                st.warning("Please select version(s) to update.")
                return
            batch_selected_versions = [selected_version]

        try:

            def on_toggle_callback(keep_forever):
                success_count = 0
                for version in batch_selected_versions:
                    with st.spinner(
                        f"Updating version {version['versionNumber']}..."
                    ):
                        success, message = (
                            self.handler.update_version_keep_forever(
                                selected_file["id"],
                                version["id"],
                                keep_forever,
                            )
                        )
                        if success:
                            success_count += 1
                        else:
                            self.ui.display_feedback_message(success, message)

                self.ui.display_feedback_message(
                    success_count > 0,
                    f"Set Keep Forever to {'ON' if keep_forever else 'OFF'} "
                    f"for {success_count} versions.",
                )
                self._clear_versions_session_state()

            self.ui.display_toggle_keep_forever_dialog(
                batch_selected_versions, on_toggle_callback
            )

        except Exception as e:
            self.ui.display_feedback_message(
                False, f"Error updating versions: {str(e)}"
            )

    def _clear_files_session_state(self):
        """Clears all session state related to files."""
        # Clear cache
        drive_id = st.session_state.get("selected_drive", {}).get("id")
        project_folder_id = st.session_state.get(
            "selected_project_folder", {}
        ).get("id")
        search_term = st.session_state.get("search_term_files")

        if drive_id and project_folder_id:
            cache_key = f"files_{drive_id}_{project_folder_id}_{search_term}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]

        # Clear file states
        keys_to_clear = [
            "selected_file",
            "files_for_display",
            "batch_selected_files",
            "search_term_files",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = None

        # Increment reset key
        st.session_state["files_reset_key"] = (
            st.session_state.get("files_reset_key", 0) + 1
        )

    def _clear_versions_session_state(self):
        """Clears all session state related to versions."""
        # Clear cache
        selected_file = st.session_state.get("selected_file")
        if selected_file and selected_file.get("id"):
            cache_key = f"versions_for_file_{selected_file['id']}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]

        # Clear version states
        keys_to_clear = ["selected_version", "batch_selected_versions"]
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = None

        # Increment reset key
        st.session_state["versions_reset_key"] = (
            st.session_state.get("versions_reset_key", 0) + 1
        )
