import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from models.general_utils import format_folder_options
import pandas as pd
from st_aggrid import JsCode


class VersionControlUI:
    def __init__(self):
        """Initialize the VersionControlUI class."""
        pass

    def _display_checkbox(self, key, label, value=False, help=""):
        """
        Display a checkbox widget in the Streamlit interface.

        Args:
            key (str): Unique key for the checkbox widget.
            label (str): Label text to display next to the checkbox.
            value (bool, optional): Initial state of the checkbox.
            Defaults to False.
            help (str, optional): Help text to display
            when hovering over the checkbox. Defaults to "".

        Returns:
            bool: Current state of the checkbox.
        """
        return st.checkbox(label, key=key, value=value, help=help)

    def show_download_button_zip(self, data, file_name, count):
        st.download_button(
            label=f"Download {count} versions as ZIP",
            data=data,
            file_name=file_name,
            mime="application/zip",
            key="download_zip_versions",
            help="Download all selected versions as a zip file",
        )

    def show_download_button_single(self, data, file_name):
        st.download_button(
            label="Download version",
            data=data,
            file_name=file_name,
            mime="application/octet-stream",
            key="download_single_version",
            help="Download the selected version",
        )

    def display_title(self, title="title"):
        """
        Display a title in the Streamlit interface.

        Args:
            title (str, optional): Title text to display. Defaults to "title".

        Returns:
            None
        """
        st.write(f"### {title}")

    def display_dataframe(self, items, key, height=400, is_versions=False):
        """
        Display a dataframe in an interactive
        AgGrid table and return selected row.

        Args:
            items (list of dict): Data to display in the table.
            key (str): Unique key for the table widget.
            height (int, optional): Height of the
            table in pixels. Defaults to 400.
            is_versions (bool, optional): Whether the
            data represents file versions. Defaults to False.

        Returns:
            dict or None: Dictionary of the selected
            row data, or None if no row is selected.
        """
        if not items:
            st.warning(
                "No files available. Note: Google "
                "Workspace files (Docs, Sheets, Slides) "
                "are not displayed here as they have "
                "their own version history system."
            )
            return None

        # Convert the list of dictionaries to a DataFrame
        # and fill missing values with empty strings
        df = pd.DataFrame(items).fillna("N/A")

        if df.empty:
            st.warning(
                "No records found. Note: Google "
                "Workspace files (Docs, Sheets, Slides) "
                "are not displayed here as they "
                "have their own version history system."
            )
            return None

        # Configure the grid options
        grid_options = self._configure_grid_options(df, is_versions)

        if not is_versions:
            st.markdown(
                """
                <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
                <div title="Note: This table shows the  most recently modified files (unless a search has been performed). Google Workspace files (Docs, Sheets, Slides) are not displayed here as they have their own version history system. Only non-Google Workspace files are shown in this table."
                    style="cursor: help; display: inline-block; font-family: 'Material Icons'; font-size: 20px; vertical-align: middle;">
                    info
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Display the DataFrame in the table
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode="SELECTION_CHANGED",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=True,
            height=height,
            key=key,
            use_container_width=True,
            fit_columns_on_grid_load=True,
        )

        # Get the selected row safely
        selected = grid_response.get("selected_rows", [])

        # Check if selected is a DataFrame and not empty
        if isinstance(selected, pd.DataFrame) and not selected.empty:
            return selected.iloc[
                0
            ].to_dict()  # Return the first selected row as a dictionary
        return None

    @st.dialog("Upload New File")
    def display_upload_new_file_dialog(
        self, folders_to_display, on_upload_callback
    ):
        """
        Display a dialog for uploading new files to selected folders.

        Args:
            folders_to_display (list): List of available folders for upload.
            on_upload_callback (function):
            Callback function to execute after upload.

        Returns:
            None
        """
        files_to_upload = self._display_file_uploader(
            label="Upload multiple files",
            key="upload_new_files_uploader",
            allow_multiple=True,
        )

        description = self._display_description_input(
            label="Description", height=90, key="upload_new_file_description"
        )

        selected_folder = self._display_folder_selectbox(
            "upload_new_file", folders_to_display
        )

        if st.button(
            "Upload", key="upload_new_file_confirm", use_container_width=True
        ):
            if not files_to_upload:
                st.warning("Please select at least one file to upload.")
                return
            if not description:
                st.warning("Please enter a description for the file(s).")
                return

            on_upload_callback(selected_folder, files_to_upload, description)
            st.rerun()

    @st.dialog("Restore file(s)")
    def display_restore_file_dialog(self, trashed_files, on_restore_callback):
        """
        Display a dialog for restoring files from trash.

        Args:
            trashed_files (list): List of files available for restoration.
            on_restore_callback (function):
            Callback function to execute after restoration.

        Returns:
            None
        """
        if not trashed_files:
            st.warning("No trashed files found.")
            return

        # Display the files in a multi-select grid
        st.write("Select files to restore:")
        selected_files = self.display_file_multi_select(
            trashed_files,
            key="restore_file_table",
        )

        if st.button(
            "Restore", key="restore_file_confirm", use_container_width=True
        ):
            if not selected_files:
                st.warning("Please select at least one file to restore.")
                return

            on_restore_callback(selected_files)
            st.rerun()

    def _display_folder_selectbox(self, key, folders_to_display):
        """
        Display a selectbox widget for folder selection.

        Args:
            key (str): Unique key for the selectbox widget.
            folders_to_display (list): List of available folders.

        Returns:
            str or None: Selected folder path, or None if no folders available.
        """
        option_labels = [
            format_folder_options(opt) for opt in folders_to_display
        ]

        if not option_labels:
            st.warning("No folders found.")
            return None

        selected_index = st.selectbox(
            "Select a folder in your project to upload the file to:",
            options=range(len(option_labels)),
            format_func=lambda i: option_labels[i],
            index=0 if option_labels else None,
            key=f"{key}_selectbox",
        )
        if selected_index is None:
            return None

        return folders_to_display[selected_index]

    @st.dialog("Revert Version")
    def display_revert_version_dialog(
        self, selected_file, selected_version, on_revert_callback
    ):
        """
        Display a dialog for reverting to a specific file version.

        Args:
            selected_file (dict): Currently selected file details.
            selected_version (dict): Version details to revert to.
            on_revert_callback (function):
            Callback function to execute after revert.

        Returns:
            None
        """
        if not selected_file:
            st.warning("Please select a file to revert a version for.")
            return
        if not selected_version:
            st.warning("Please select a version to revert to.")
            return

        st.write(f"Selected File: {selected_file['name']}")
        st.write(
            f"Selected Version: {selected_version['versionNumber']} "
            f"with name {selected_version['originalFilename']}"
        )

        description = self._display_description_input(
            label="Description",
            height=90,
            key="revert_version_description",
            help=(
                "Enter a description for the revert. "
                "A default description will be added "
                "automatically explaining the revert."
            ),
        )

        if st.button(
            "Confirm", key="revert_version_confirm", use_container_width=True
        ):
            if not description:
                st.warning("Please enter a description for the revert.")
                return

            on_revert_callback(selected_file, selected_version, description)
            st.rerun()

    @st.dialog("Move File(s)")
    def display_move_file_dialog(
        self, selected_files, folders_to_display, on_move_callback
    ):
        """
        Display a dialog for moving files to a different folder.

        Args:
            selected_files (list): List of selected files to move.
            folders_to_display (list): Available destination folders.
            on_move_callback (function):
            Callback function to execute after moving.

        Returns:
            None
        """
        if not selected_files:
            st.warning("Please select file(s) to move.")
            return

        # Display selected files
        st.write(f"Selected {len(selected_files)} file(s) to move:")
        with st.expander("View selected files"):
            for file in selected_files:
                st.write(
                    f"- {file['name']} "
                    f"(in {file.get('folder_name', 'N/A')})"
                )

        # Display a selectbox with all folders
        folder_labels = [
            format_folder_options(opt) for opt in folders_to_display
        ]
        if not folder_labels:
            st.warning("No folders found.")
            return

        selected_index = st.selectbox(
            "Select a folder in your project to move the file(s) to:",
            options=range(len(folder_labels)),
            format_func=lambda i: folder_labels[i],
            index=0 if folder_labels else None,
            key="move_file_selectbox",
        )

        if selected_index is None:
            return

        selected_folder = folders_to_display[selected_index]

        # Add "Move" and "Cancel" buttons
        if st.button(
            "Confirm", key="move_file_confirm", use_container_width=True
        ):
            on_move_callback(selected_files, selected_folder)
            st.rerun()

    @st.dialog("Rename File")
    def display_rename_file_dialog(self, selected_file, on_rename_callback):
        """
        Display a dialog for renaming a file.

        Args:
            selected_file (dict): File details to be renamed.
            on_rename_callback (function):
            Callback function to execute after rename.

        Returns:
            None
        """
        if not selected_file:
            st.warning("Please select a file to rename.")
            return

        st.write(f"Selected File: {selected_file['name']}")

        new_name = st.text_input(
            "Enter the new name for the file:",
            key="rename_file_new_name",
            value=selected_file["name"],
        )

        if st.button(
            "Rename", key="rename_file_confirm", use_container_width=True
        ):
            if not new_name:
                st.warning("Please enter a new name for the file.")
                return

            on_rename_callback(selected_file, new_name)
            st.rerun()

    @st.dialog("Delete File(s)")
    def display_delete_file_dialog(self, selected_files, on_delete_callback):
        """
        Display a dialog for deleting files either permanently or to trash.

        Args:
            selected_files (list or dict): File(s) to be deleted.
            on_delete_callback (function):
            Callback function to execute after deletion.

        Returns:
            None
        """
        if not selected_files:
            st.warning("Please select file(s) to delete.")
            return

        # Convert single file to list for consistent handling
        if isinstance(selected_files, dict):
            selected_files = [selected_files]

        st.write(f"**{len(selected_files)} file(s) selected for deletion:**")
        with st.expander("View selected files"):
            for file in selected_files:
                st.write(f"- {file['name']}")

        st.write("**Warning:** This action cannot be undone.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "Delete forever",
                key="delete_file_confirm",
                help="This action will delete the file(s) permanently.",
                use_container_width=True,
            ):
                for file in selected_files:
                    on_delete_callback(file, delete_permanently=True)
                st.rerun()

        with col2:
            if st.button(
                "Move to trash",
                key="move_to_trash_confirm",
                help="This action will move the file(s) to trash.",
                use_container_width=True,
            ):
                for file in selected_files:
                    on_delete_callback(file, delete_permanently=False)
                st.rerun()

    @st.dialog("Delete Version(s)")
    def display_delete_versions_dialog(
        self, selected_versions, on_delete_callback
    ):
        """
        Display a dialog for deleting file versions.

        Args:
            selected_versions (list): Versions to be deleted.
            on_delete_callback (function):
            Callback function to execute after deletion.

        Returns:
            None
        """
        if not selected_versions:
            st.warning("Please select version(s) to delete.")
            return

        st.write(
            f"**{len(selected_versions)} version(s) selected for deletion:**"
        )
        with st.expander("View selected versions"):
            for version in selected_versions:
                st.write(
                    f"- {version['originalFilename']} "
                    f"(Version {version['versionNumber']})"
                )

        st.write("**Warning:** This action cannot be undone.")

        if st.button(
            "Delete forever",
            key="delete_versions_confirm",
            use_container_width=True,
        ):
            on_delete_callback(selected_versions)
            st.rerun()

    def display_search(self):
        """
        Display a search input field for filtering files.

        Returns:
            str: The current search term entered by the user.
        """
        return st.text_input(
            "Search files by name",
            key="Search_files",
            placeholder="Search for additional files...",
        )

    def display_feedback_message(self, success, message):
        """
        Display a success or error feedback message.

        Args:
            success (bool): Whether the operation was successful.
            message (str): Feedback message to display.

        Returns:
            None
        """
        if success:
            st.success(message)
        else:
            st.error(message)

    def display_file_multi_select(self, files, key):
        """
        Display a multi-select widget for files with select all option.

        Args:
            files (list): List of files to display in the widget.
            key (str): Unique key for the widget.

        Returns:
            list: Selected files from the widget.
        """
        if not files:
            return []

        # Create display names with folder info if available
        options = [
            f"{f['name']} (in {f.get('folder_name', 'N/A')})" for f in files
        ]

        # Add a "Select All" checkbox
        col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
        with col2:
            select_all = st.checkbox(
                "Select All",
                key=f"{key}_select_all",
                value=False,
                help="Select/Deselect all files",
            )

        # Use a multi-select widget
        with col1:
            if select_all:
                selected_indices = st.multiselect(
                    "Select files for batch operations:",
                    options=options,
                    default=options,
                    key=f"{key}_multiselect",
                )
            else:
                selected_indices = st.multiselect(
                    "Select files for batch operations:",
                    options=options,
                    key=f"{key}_multiselect",
                )

        # Map back to file IDs
        selected_files = []
        for idx, option in enumerate(options):
            if option in selected_indices:
                selected_files.append(files[idx])

        return selected_files

    def display_version_multi_select(
        self,
        versions,
        key,
        disabled=False,
        placeholder="No versions available",
    ):
        """
        Display a multi-select widget for versions with select all option.

        Args:
            versions (list): List of versions to display.
            key (str): Unique key for the widget.
            disabled (bool, optional):
            Whether to disable the widget. Defaults to False.
            placeholder (str, optional):
            Placeholder text when no versions available.
            Defaults to "No versions available".

        Returns:
            list: Selected versions from the widget.
        """
        # Create display names with version info if available
        options = (
            [
                f"{v['originalFilename']} (Version {v['versionNumber']})"
                for v in versions
            ]
            if versions
            else []
        )

        # Disable multiselect if no options available
        is_disabled = disabled or not options
        final_placeholder = (
            placeholder
            if not options
            else "Select versions for batch operations:"
        )

        if is_disabled:
            st.caption(final_placeholder)
            return []

        # Add a "Select All" checkbox
        col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
        with col2:
            select_all = st.checkbox(
                "Select All",
                key=f"{key}_select_all",
                value=False,
                help="Select/Deselect all versions",
                disabled=is_disabled,
            )

        # Use a multi-select widget
        with col1:
            if select_all:
                selected_indices = st.multiselect(
                    "Select versions for batch operations:",
                    options=options,
                    default=options,
                    key=f"{key}_multiselect",
                    disabled=is_disabled,
                    placeholder=final_placeholder,
                )
            else:
                selected_indices = st.multiselect(
                    "Select versions for batch operations:",
                    options=options,
                    key=f"{key}_multiselect",
                    disabled=is_disabled,
                    placeholder=final_placeholder,
                )

        # Map back to version dictionaries
        selected_versions = []
        for idx, option in enumerate(options):
            if option in selected_indices:
                selected_versions.append(versions[idx])

        return selected_versions

    @st.dialog("Toggle Keep Forever")
    def display_toggle_keep_forever_dialog(
        self, selected_versions, on_toggle_callback
    ):
        """
        Display a dialog for toggling the 'keepForever' status of file versions.

        Args:
            selected_versions (list): List of version dictionaries to modify.
            on_toggle_callback (function): Callback function to execute when
                changes are confirmed. Receives the new keepForever status as
                argument.

        Returns:
            None
        """
        st.write(f"**{len(selected_versions)} version(s) selected:**")
        with st.expander("View selected versions"):
            for version in selected_versions:
                current_status = version.get("keepForever", False)
                st.write(
                    f"- {version['originalFilename']} (V{version['versionNumber']}) - {'✅ Keep Forever' if current_status else '❌ Auto-expire'}"
                )

        # Simple checkbox for the new status
        keep_forever = st.checkbox(
            "Keep Forever",
            value=any(v.get("keepForever", False) for v in selected_versions),
            key="keep_forever_checkbox",
        )

        if st.button(
            "Apply",
            key="apply_keep_forever",
            use_container_width=True,
        ):
            on_toggle_callback(keep_forever)
            st.rerun()

    @st.dialog("Rename Multiple Files")
    def display_rename_files_dialog(self, selected_files, on_rename_callback):
        """
        Display a dialog for batch renaming
        multiple files with various renaming options.

        Args:
            selected_files (list): List of file dictionaries to be renamed.
            on_rename_callback (function):
            Callback function to execute with the new names.
            Receives a dictionary mapping file IDs to new names.

        Returns:
            None
        """
        if not selected_files:
            st.warning("Please select files to rename.")
            return

        st.write(f"Selected {len(selected_files)} files for renaming:")

        # Display current names
        with st.expander("Current File Names"):
            for file in selected_files:
                st.write(f"- {file['name']}")

        # Renaming options
        rename_option = st.radio(
            "Rename option:",
            options=[
                "Add prefix to all files",
                "Add suffix to all files",
                "Replace text in all files",
                "Custom rename for each file",
            ],
            key="rename_files_option",
        )

        new_names = {}

        if rename_option in [
            "Add prefix to all files",
            "Add suffix to all files",
        ]:
            text = st.text_input(
                f"Enter text to {rename_option.split(' ')[1].lower()}:",
                key="rename_files_text",
            )

            if rename_option == "Add prefix to all files":
                new_names = {
                    f["id"]: f"{text}{f['name']}" for f in selected_files
                }
            else:
                new_names = {
                    f["id"]: f"{f['name']}{text}" for f in selected_files
                }

        elif rename_option == "Replace text in all files":
            old_text = st.text_input(
                "Text to replace:", key="rename_files_old_text"
            )
            new_text = st.text_input(
                "Replace with:", key="rename_files_new_text"
            )

            new_names = {
                f["id"]: f["name"].replace(old_text, new_text)
                for f in selected_files
            }

        else:  # Custom rename for each file
            for file in selected_files:
                new_name = st.text_input(
                    f"New name for {file['name']}:",
                    value=file["name"],
                    key=f"rename_file_{file['id']}",
                )
                new_names[file["id"]] = new_name

        if st.button(
            "Rename Files",
            key="rename_files_confirm",
            use_container_width=True,
        ):
            if not all(new_names.values()):
                st.warning("Please enter new names for all files.")
                return

            on_rename_callback(new_names)
            st.rerun()

    @st.dialog("Upload version")
    def display_upload_new_version_dialog(
        self, selected_file, on_upload_callback
    ):
        """
        Display a dialog for uploading new versions
        of an existing file with advanced options.

        Args:
            selected_file (dict): Dictionary containing
            details of the file to version.
            on_upload_callback (function):
            Callback function to execute when versions are uploaded.
            Receives file details, upload files, description,
            keep_forever status, change_file_type flag, and
            keep_only_latest_version flag.

        Returns:
            None
        """
        if not selected_file:
            st.warning("Please select a file to upload a new version for.")
            return

        st.write(f"Selected File: {selected_file['name']}")

        files_to_upload = self._display_file_uploader(
            label="Upload a new version",
            key="upload_version_file",
            allow_multiple=True,
        )

        # Add ordering functionality
        if files_to_upload:
            st.write("**Select upload order:**")
            order_options = {
                "As selected (first file will be oldest version)": "selected",
                "Reverse order (last file will be oldest version)": "reverse",
                "Alphabetical by filename": "alphabetical",
                "Newest first (by modified date)": "newest_first",
                "Oldest first (by modified date)": "oldest_first",
            }

            selected_order = st.selectbox(
                "Version creation order:",
                options=list(order_options.keys()),
                key="version_upload_order",
            )

            # Apply ordering
            if order_options[selected_order] == "reverse":
                files_to_upload = list(reversed(files_to_upload))
            elif order_options[selected_order] == "alphabetical":
                files_to_upload = sorted(files_to_upload, key=lambda x: x.name)
            elif order_options[selected_order] == "newest_first":
                files_to_upload = sorted(
                    files_to_upload,
                    key=lambda x: x.size,
                    reverse=True,
                )
            elif order_options[selected_order] == "oldest_first":
                files_to_upload = sorted(files_to_upload, key=lambda x: x.size)

        description = self._display_description_input(
            label="Description",
            height=90,
            key="upload_version_description",
        )

        keep_forever = self._display_checkbox(
            key="keep_forever",
            label="Keep version(s) forever",
            help=(
                "Whether to keep this version forever, even if it "
                "is no longer the head/current version. "
                "If not set, the version will be automatically "
                "purged 30 days after newer content is uploaded. "
                "This can be set on a maximum of 200 revisions for a file."
            ),
        )

        keep_only_latest_version = self._display_checkbox(
            key="keep_only_latest_version",
            label="Keep only the latest version",
            help=(
                "Whether to keep only the latest version of the file. "
                "If set to True, the current version will be updated "
                "with the new version and all other versions will be deleted. "
            ),
        )
        change_file_type = self._display_checkbox(
            key="change_file_type",
            label="Change file type to match new version",
            help="If checked, the main file's type will "
            "be updated to match the new version",
            value=False,
        )

        if st.button(
            "Confirm", key="upload_version_confirm", use_container_width=True
        ):
            if not files_to_upload:
                st.warning("Please select at least one file to upload.")
                return
            if not description:
                st.warning("Please enter a description for the new version.")
                return

            on_upload_callback(
                selected_file,
                files_to_upload,
                description,
                keep_forever,
                change_file_type,
                keep_only_latest_version,
            )
            st.rerun()

    def _display_file_uploader(
        self, key, label="Upload a file", allow_multiple=False
    ):
        """
        Display a file uploader widget.

        Args:
            key (str): Unique key for the widget.
            label (str, optional): Label text to display above the uploader.
            Defaults to "Upload a file".
            allow_multiple (bool, optional): Whether to
            allow multiple file uploads. Defaults to False.

        Returns:
            UploadedFile or list: The uploaded file(s) as
            BytesIO object(s), or None if no file uploaded.
        """
        return st.file_uploader(
            label, key=key, accept_multiple_files=allow_multiple
        )

    def _display_description_input(
        self, key, label="Description:", value="", height=90, help=""
    ):
        """
        Display a text area input for descriptions.

        Args:
            key (str): Unique key for the widget.
            label (str, optional): Label text to display above the input.
            Defaults to "Description:".
            value (str, optional): Initial text content. Defaults to "".
            height (int, optional): Height of the
            text area in pixels. Defaults to 90.
            help (str, optional): Help text to
            display when hovering. Defaults to "".

        Returns:
            str: The text entered by the user.
        """
        return st.text_area(
            label=label, key=key, value=value, height=height, help=help
        )

    def display_button(
        self, key, label="Button", use_container_width=False, help=""
    ):
        """
        Display a clickable button widget.

        Args:
            key (str): Unique key for the widget.
            label (str, optional): Text to display on the button.
            Defaults to "Button".
            use_container_width (bool, optional): Whether
            to expand button to container width. Defaults to False.
            help (str, optional): Help text to
            display when hovering. Defaults to "".

        Returns:
            bool: True if the button was clicked
            in the current run, False otherwise.
        """
        return st.button(
            label,
            key=key,
            use_container_width=use_container_width,
            help=help,
        )

    def _configure_grid_options(self, df, is_versions=False):
        """
        Configure options for the AgGrid display
        based on the DataFrame content.

        Args:
            df (pd.DataFrame): Data to display in the grid.
            is_versions (bool, optional): Whether the data
            represents file versions. Defaults to False.

        Returns:
            dict: Configured grid options dictionary for AgGrid.
        """
        if is_versions:
            # Define the desired column order for versions
            desired_order = [
                "versionNumber",
                "originalFilename",
                "description",
                "modifiedTime",
                "keepForever",
                "mimeType",
                "size",
            ]
        else:
            # Define the desired column order for files
            desired_order = [
                "name",
                "description",
                "folder_name",
                "createdTime",
                "modifiedTime",
                "size",
                "mimeType",
                "webViewLink",
                "webContentLink",
            ]

        # Ensure all desired columns are present in the DataFrame
        for col in desired_order:
            if col not in df.columns:
                df[col] = None  # Add missing columns with default values
        df = df.loc[:, desired_order]

        # Optionally convert to datetime (if needed)
        if "createdTime" in df.columns:
            df["createdTime"] = pd.to_datetime(
                df["createdTime"], errors="coerce"
            )
        if "modifiedTime" in df.columns:
            df["modifiedTime"] = pd.to_datetime(
                df["modifiedTime"], errors="coerce"
            )

        # Configure the grid options
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection("single", use_checkbox=True)
        gb.configure_grid_options(
            suppressContextMenu=True,
            clipboard=True,
            enableBrowserTooltips=True,
            enableRangeSelection=True,
            suppressCopyRowsToClipboard=False,
            animateRows=True,
        )
        gb.configure_default_column(
            resizable=True,
            enableCellTextSelection=True,
            editable=False,
            sortable=True,
            wrapText=False,
            minWidth=100,
        )

        # JavaScript date formatter
        date_formatter = JsCode(
            """
            function(params) {
                if (!params.value) return '';
                const date = new Date(params.value);
                return date.toLocaleString();
            }
        """
        )

        if is_versions:
            # Configure columns for versions
            gb.configure_column(
                "versionNumber",
                headerName="N°",
                pinned="left",
                checkboxSelection=True,
                filter="agNumberColumnFilter",
                sort="desc",
            )
            gb.configure_column(
                "originalFilename",
                headerName="Name",
                filter="agTextColumnFilter",
            )
            gb.configure_column(
                "keepForever",
                headerName="Keep Forever",
                filter="agSetColumnFilter",
            )
        else:
            # Configure columns for files
            gb.configure_column(
                "name",
                headerName="Name",
                pinned="left",
                checkboxSelection=True,
                filter="agTextColumnFilter",
                minWidth=200,
            )
            if "folder_name" in df.columns:
                gb.configure_column(
                    "folder_name",
                    headerName="Folder",
                    filter="agTextColumnFilter",
                )
            if "webViewLink" in df.columns:
                gb.configure_column(
                    "webViewLink",
                    headerName="Link",
                    cellStyle={
                        "cursor": "pointer",
                        "color": "#AB47BC",
                        "text-decoration": "underline",
                    },
                )
            if "webContentLink" in df.columns:
                gb.configure_column(
                    "webContentLink",
                    headerName="Download Link",
                    cellStyle={
                        "cursor": "pointer",
                        "color": "#AB47BC",
                        "text-decoration": "underline",
                    },
                )

        if "description" in df.columns:
            gb.configure_column(
                "description",
                headerName="Description",
                cellStyle={
                    "whiteSpace": "pre-line",
                    "wordWrap": "break-word",
                },  # Use 'pre-line' to preserve line breaks
                filter="agTextColumnFilter",
                wrapText=True,
            )

        if "modifiedTime" in df.columns:
            gb.configure_column(
                "modifiedTime",
                headerName="Modified Time",
                valueFormatter=date_formatter,
                sort="desc",
                minWidth=150,
            )
        if "createdTime" in df.columns:
            gb.configure_column(
                "createdTime",
                headerName="Created Time",
                valueFormatter=date_formatter,
                minWidth=150,
            )
        if "size" in df.columns:
            gb.configure_column(
                "size",
                headerName="Size",
                type=["numericColumn"],
                filter="agNumberColumnFilter",
            )
        if "mimeType" in df.columns:
            gb.configure_column(
                "mimeType",
                headerName="Type",
                type=["textColumn"],
                filter="agSetColumnFilter",
            )

        # Hid the necessary columns
        if "id" in df.columns:
            gb.configure_column("id", headerName="id", hide=True)
        if not is_versions and "folder_id" in df.columns:
            gb.configure_column("folder_id", headerName="folder_id", hide=True)

        if not is_versions:
            cell_clicked = JsCode(
                """
                function(params) {
                    // Check if the clicked column is the URL column
                    if ((params.colDef.field === 'webViewLink' || params.colDef.field === 'webContentLink')
                        && params.value && params.value !== 'N/A') {
                        // Open the URL in a new tab
                        window.open(params.value, '_blank');
                    }
                }
                """
            )

            grid_options = gb.build()
            grid_options["onCellClicked"] = cell_clicked.js_code
        else:
            grid_options = gb.build()

        return grid_options
