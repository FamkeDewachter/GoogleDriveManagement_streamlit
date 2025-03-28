from views.comment_ui import CommentUI
from handlers.comments_handler import CommentsHandler
import streamlit as st


class CommentController:
    def __init__(self, drive_service, user_name):
        """
        Initialize the Comment Controller with the necessary services
        and UI components.
        """
        self.handler = CommentsHandler(drive_service, user_name)
        self.ui = CommentUI(user_name)

    def start(self, width_ratio=3):
        """Handle comments for the selected file version."""
        if not st.session_state.get(
            "selected_file"
        ) or not st.session_state.get("selected_version"):
            st.session_state.pop("selected_file", None)
            st.session_state.pop("selected_version", None)
            st.session_state.pop("comments", None)

        self.ui.display_title()

        col_selection, col_comments = st.columns([1, width_ratio])
        col_empty, col_chat_input = st.columns([1, width_ratio])

        with col_selection:
            self._handle_and_display_files()
            self._handle_and_display_versions()

        with col_comments:
            self._handle_and_display_comments()

        with col_chat_input:
            self._handle_and_display_new_comment()

    def _clear_session_keys(self, keys):
        for key in keys:
            st.session_state.pop(key, None)

    def _handle_and_display_files(self):
        """Handle and display the files, with search functionality."""
        # Initialize all necessary session state variables
        self._initialize_file_state()

        # Display search bar and get search term
        search_term = self.ui.display_searchbar_files(
            placeholder="Search files..."
        )

        # Determine which files to display based on search
        if search_term:
            self._handle_file_search(search_term)
            files_to_display = st.session_state.searched_files
        else:
            self._handle_recent_files()
            files_to_display = st.session_state.all_files
            # Clear search-related state when no search term
            self._clear_session_keys(["searched_files", "last_search_term"])

        # Display file selection UI
        self._display_file_selection(files_to_display)

    def _initialize_file_state(self):
        """Initialize all file-related session state variables."""
        st.session_state.setdefault("all_files", None)
        st.session_state.setdefault("searched_files", None)
        st.session_state.setdefault("last_search_term", "")
        st.session_state.setdefault("selected_file", None)
        st.session_state.setdefault("comments", None)
        st.session_state.setdefault("all_versions", None)

    def _handle_file_search(self, search_term):
        """Handle file search functionality."""
        if (
            st.session_state.searched_files is None
            or st.session_state.last_search_term != search_term
        ):
            with st.spinner("Searching files..."):
                gds_files = self.handler.get_files_in_project_with_search_term(
                    search_term
                )
                st.session_state.searched_files = self._process_and_map_files(
                    gds_files
                )
                st.session_state.last_search_term = search_term

    def _handle_recent_files(self):
        """Handle fetching recent files if not already loaded."""
        if st.session_state.all_files is None:
            gds_files = self.handler.get_recent_files_in_project()
            st.session_state.all_files = self._process_and_map_files(gds_files)

    def _process_and_map_files(self, gds_files):
        """Common method to process files and map folder info."""
        if not gds_files:
            return []

        folder_ids = list(
            {
                parent
                for file in gds_files
                for parent in file.get("parents", [])
                if parent is not None
            }
        )

        folders_with_name = self.handler.get_folders_info(
            folder_ids, fields="id, name"
        )

        return self.handler.add_folder_info_to_files(
            gds_files, folders_with_name
        )

    def _display_file_selection(self, files_to_display):
        """Display file selection UI and handle selection changes."""
        selected_file = self.ui.display_selectbox_files(
            label="Select a file:",
            files=files_to_display if files_to_display else None,
            placeholder="No files found",
        )

        if (
            "selected_file" in st.session_state
            and st.session_state.selected_file != selected_file
        ):
            self._reset_file_selection_state()

        st.session_state.selected_file = selected_file

    def _reset_file_selection_state(self):
        """Reset state when file selection changes."""
        st.session_state.selected_version = None
        st.session_state.comments = None
        st.session_state.filter_criteria = None
        self._clear_filter_state()

    def _handle_and_display_versions(self):
        """Handle and display the versions, only re-fetch if needed."""
        selected_file = st.session_state.selected_file

        # Initialize session state variables
        self._initialize_version_state()

        # Load versions if needed
        self._load_versions_if_needed(selected_file)

        # Display version selection UI
        selected_version = self.ui.display_selectbox_versions(
            versions=st.session_state.all_versions if selected_file else None,
        )

        self._handle_version_change(selected_version)

        self._handle_version_download(selected_file, selected_version)

        self._handle_version_preview(selected_version)

    def _initialize_version_state(self):
        """Initialize all version-related session state variables."""
        st.session_state.setdefault("all_versions", None)
        st.session_state.setdefault("last_selected_file", None)
        st.session_state.setdefault("version_preview_content", None)
        st.session_state.setdefault("last_selected_version_id", None)

    def _load_versions_if_needed(self, selected_file):
        """Load versions if the selected file has changed or versions aren't loaded."""
        if selected_file and (
            st.session_state.all_versions is None
            or st.session_state.last_selected_file != selected_file
        ):
            with st.spinner("Loading versions..."):
                st.session_state.all_versions = (
                    self.handler.get_sorted_versions_of_a_file(selected_file)
                )
                st.session_state.last_selected_file = selected_file
                st.session_state.version_preview_content = None
                st.session_state.last_selected_version_id = None

    def _handle_version_change(self, selected_version):
        """Handle state changes when version selection changes."""
        if (
            "selected_version" in st.session_state
            and st.session_state.selected_version != selected_version
        ):
            st.session_state.comments = None
            st.session_state.filter_criteria = None
            self._clear_filter_state()
            st.session_state.version_preview_content = None

        st.session_state.selected_version = selected_version

    def _handle_version_preview(self, selected_version):
        """Handle loading and displaying version preview with appropriate messages."""
        if not selected_version:
            return

        current_version_id = selected_version["id"]
        last_version_id = st.session_state.get("last_selected_version_id")
        is_image = self._is_image_file(selected_version["name"])

        # Only load preview if version changed or preview isn't loaded yet
        if (
            current_version_id != last_version_id
            or st.session_state.version_preview_content is None
        ):
            if is_image:
                st.session_state.version_preview_content = (
                    self.handler.get_version_media_content(
                        st.session_state.selected_file["id"],
                        current_version_id,
                    )
                )
            else:
                st.session_state.version_preview_content = None
                st.info("No preview available for this file type")

            st.session_state.last_selected_version_id = current_version_id
        else:
            # If we already have content but it's not an image file
            if (
                not is_image
                and st.session_state.version_preview_content is None
            ):
                st.info("No preview available for this file type")

        # Display preview if available (only for images)
        if is_image and st.session_state.version_preview_content:
            self.ui.display_version_preview(
                st.session_state.version_preview_content, "image"
            )

    @staticmethod
    def _is_image_file(filename):
        """Check if the filename indicates an image file."""
        return any(
            ext in filename.lower()
            for ext in [".jpg", ".jpeg", ".png", ".gif"]
        )

    def _clear_filter_state(self):
        """Clear all filter-related session state."""
        self._clear_session_keys(
            [
                "comment_status_filter",
                "comment_user_filter",
                "comment_search_filter",
            ]
        )

    def _handle_and_display_comments(self):
        """Main method to handle and display comments."""
        if (
            st.session_state.selected_file
            and st.session_state.selected_version
        ):
            self.ui.display_header(
                st.session_state.selected_file,
                st.session_state.selected_version,
            )
            self._load_comments_if_needed()
            self._display_comments()

    def _load_comments_if_needed(self):
        """Load comments if they haven't been loaded yet."""
        if (
            "comments" not in st.session_state
            or st.session_state.comments is None
        ):
            st.session_state.comments = self.handler.get_comments_of_version(
                st.session_state.selected_file,
                st.session_state.selected_version,
            )

    def _display_comments(self):
        if st.session_state.get("comments") is not None:
            self._handle_comment_filters()

        # Create and display the comments container
        container_comment = self.ui.display_container(height=400, border=True)
        with container_comment:
            if st.session_state.comments:
                # Get filtered comments based on session state criteria
                filtered_comments = self._get_filtered_comments()

                if filtered_comments:
                    for comment in filtered_comments:
                        action = self.ui.display_comment(comment)
                        self._handle_comment_action(action)
                else:
                    st.warning("No comments match the selected filters.")
            else:
                self.ui.display_no_comments_message()

    def _handle_comment_filters(self):
        """Handle comment filters and update session state accordingly."""
        if not st.session_state.get("comments"):
            return

        # Get filter criteria from UI
        filter_criteria = self.ui.display_comments_filters(
            st.session_state.comments
        )

        # If filters were cleared (empty search text and 'all' for other filters)
        if (
            filter_criteria
            and filter_criteria.get("search_text") == ""
            and filter_criteria.get("status") == "all"
            and filter_criteria.get("user_filter") == "all"
        ):
            # Clear filter-related session state
            self._clear_filter_state()
            st.session_state.filter_criteria = None
            st.rerun()
        elif filter_criteria is not None:
            # Update filter criteria in session state
            st.session_state.filter_criteria = filter_criteria
            st.rerun()

    def _get_filtered_comments(self):
        """Apply filters to comments based on session state criteria."""
        if not st.session_state.comments:
            return []

        # Ensure filter_criteria is always a dictionary
        filter_criteria = st.session_state.get("filter_criteria") or {
            "status": "all",
            "search_text": "",
            "user_filter": "all",
        }

        filtered_comments = st.session_state.comments.copy()

        # Apply status filter
        if filter_criteria.get("status", "all") != "all":
            resolved_status = filter_criteria["status"] == "resolved"
            filtered_comments = [
                c
                for c in filtered_comments
                if c.get("resolved", False) == resolved_status
            ]

        # Apply user filter
        if filter_criteria.get("user_filter", "all") != "all":
            filtered_comments = [
                c
                for c in filtered_comments
                if c["user"] == filter_criteria["user_filter"]
            ]

        # Apply search text filter
        if filter_criteria.get("search_text", ""):
            search_text = filter_criteria["search_text"].lower()
            filtered_comments = [
                c
                for c in filtered_comments
                if search_text in c["content"].lower()
            ]

        return filtered_comments

    def _handle_comment_action(self, action):
        """Handle comment actions"""
        if (
            not action
            or not isinstance(action, dict)
            or "id" not in action
            or "action" not in action
        ):
            return

        item_id = action["id"]
        action_type = action["action"]

        try:
            if action_type == "delete":
                self._confirm_and_delete_comment(item_id)
            elif action_type == "delete_reply":
                self._confirm_and_delete_reply(item_id)
            elif action_type in ["resolve", "unresolve"]:
                self._handle_comment_resolve(item_id, action_type == "resolve")
            elif action_type == "edit":
                self._handle_comment_edit(item_id)
            elif action_type == "reply":
                self._handle_comment_reply(item_id)

        except Exception as e:
            st.error(f"Failed to {action_type} comment: {e}")

    def _confirm_and_delete_comment(self, comment_id):
        """Handle the confirmation and deletion of a comment."""
        comment_to_delete = next(
            (c for c in st.session_state.comments if c["id"] == comment_id),
            None,
        )
        if not comment_to_delete:
            return

        def on_confirm():
            self._handle_comment_deletion(comment_id)
            st.rerun()

        self.ui.display_delete_confirmation_dialog(
            content_to_delete=comment_to_delete["content"],
            on_confirm_callback=on_confirm,
            on_cancel_callback=lambda: st.rerun(),
        )

    def _handle_comment_deletion(self, comment_id):
        """Handle the deletion of a comment."""
        with st.spinner("Deleting comment..."):
            self.handler.delete_comment(
                st.session_state.selected_file,
                st.session_state.selected_version,
                comment_id,
            )
            # Update session state by filtering out the deleted comment
            st.session_state.comments = [
                c for c in st.session_state.comments if c["id"] != comment_id
            ]
            st.rerun()

    def _handle_comment_resolve(self, comment_id, resolved):
        """Handle resolving or unresolving a comment."""
        with st.spinner("Updating comment status..."):
            self.handler.update_resolve_comment(
                st.session_state.selected_file,
                st.session_state.selected_version,
                comment_id,
                resolved,
            )
            # Update the comment's resolved status in session state
            for comment in st.session_state.comments:
                if comment["id"] == comment_id:
                    comment["resolved"] = resolved
                    break
            st.rerun()

    def _handle_and_display_new_comment(self):
        selected_file = st.session_state.selected_file
        selected_version = st.session_state.selected_version

        if not selected_file or not selected_version:
            st.info("Please select a file and version to comment on.")
            return
        comment_text = self.ui.display_chat_input()

        if comment_text and selected_file and selected_version:
            with st.spinner("Posting comment..."):
                new_comment = self.handler.save_new_comment(
                    selected_file, selected_version, comment_text
                )

                # Initialize comments in session state if not already
                # and append the new comment
                if (
                    "comments" not in st.session_state
                    or st.session_state.comments is None
                ):
                    st.session_state.comments = []

                if new_comment:
                    st.session_state.comments.append(new_comment)
                    st.rerun()

    def _handle_comment_edit(self, comment_id):
        """Handle the editing of a comment's content."""
        # Find the comment to edit
        comment_to_edit = next(
            (c for c in st.session_state.comments if c["id"] == comment_id),
            None,
        )

        if not comment_to_edit:
            st.error("Comment not found")
            return

        # Display the edit dialog
        def on_edit_callback(new_content):
            if new_content and new_content != comment_to_edit["content"]:
                with st.spinner("Updating comment..."):
                    try:
                        # Update the comment in the database
                        self.handler.update_comment_content(
                            st.session_state.selected_file,
                            st.session_state.selected_version,
                            comment_id,
                            new_content,
                        )
                        # Update the comment in session state
                        comment_to_edit["content"] = new_content
                        st.success("Comment updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update comment: {e}")

        # Show the edit dialog
        self.ui.display_edit_dialog(
            comment_to_edit["content"],
            on_edit_callback,
            on_cancel_callback=lambda: st.rerun(),
        )

    def _handle_comment_reply(self, comment_id):
        """Handle the editing of a comment's content."""
        # Find the comment to edit
        comment_to_reply = next(
            (c for c in st.session_state.comments if c["id"] == comment_id),
            None,
        )

        if not comment_to_reply:
            st.error("Comment not found")
            return

        # Display the edit dialog
        def on_reply_callback(reply_text):
            if reply_text:
                with st.spinner("Posting reply..."):
                    try:
                        # Save the reply to the database
                        new_reply = self.handler.save_reply(
                            st.session_state.selected_file,
                            st.session_state.selected_version,
                            comment_id,
                            reply_text,
                        )

                        # Update the comment in session state with the new reply
                        for comment in st.session_state.comments:
                            if comment["id"] == comment_id:
                                comment.setdefault("replies", []).append(
                                    new_reply
                                )
                                break

                        st.success("Successfully replied to comment!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update comment: {e}")

        # Show the edit dialog
        self.ui.display_reply_dialog(
            comment_to_reply["content"],
            comment_to_reply["user"],
            on_reply_callback,
            on_cancel_callback=lambda: st.rerun(),
        )

    def _confirm_and_delete_reply(self, reply_id):
        """Handle the confirmation and deletion of a reply."""
        reply_to_delete = None
        for comment in st.session_state.get("comments", []):
            for reply in comment.get("replies", []):
                if reply["id"] == reply_id:
                    reply_to_delete = reply
                    break
            if reply_to_delete:
                break

        if not reply_to_delete:
            return

        def on_confirm():
            self._handle_reply_deletion(reply_id)
            st.rerun()

        self.ui.display_delete_confirmation_dialog(
            content_to_delete=reply_to_delete["content"],
            on_confirm_callback=on_confirm,
            on_cancel_callback=lambda: st.rerun(),
            is_reply=True,
        )

    def _handle_reply_deletion(self, reply_id):
        with st.spinner("Deleting reply..."):
            self.handler.delete_reply(
                st.session_state.selected_file,
                st.session_state.selected_version,
                reply_id,
            )

            # Update the session state comments by filtering out the deleted reply
            for comment in st.session_state.get("comments", []):
                comment.setdefault("replies", [])
                comment["replies"] = [
                    r for r in comment["replies"] if r["id"] != reply_id
                ]

        st.rerun()

    def _handle_version_download(self, selected_file, selected_version):
        """Handle downloading of a selected version."""
        if not selected_version:
            return

        if self.ui.show_prepare_download_button():
            with st.spinner("Preparing download..."):
                file_id = selected_file["id"]
                version_id = selected_version["id"]

                file_bytes, mime_type = self.handler.get_version_content(
                    file_id, version_id
                )
                print("mime_type", mime_type)
                if file_bytes:
                    # Determine filename
                    if selected_version.get("name"):
                        file_name = selected_version["name"]
                        # Remove "(current version)" from filename if it exists
                        file_name = file_name.replace(" (current version)", "")

                    # Use UI method for download button
                    self.ui.show_download_button(
                        file_bytes, file_name, mime_type
                    )
                else:
                    st.error("Failed to prepare download")
