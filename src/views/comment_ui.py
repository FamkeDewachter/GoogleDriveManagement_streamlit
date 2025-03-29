import streamlit as st
from models.general_utils import format_file_options


class CommentUI:
    def __init__(self, user_name):
        """Initializes the CommentUI class."""
        self.user_name = user_name

    def display_title(self):
        """Displays the app title."""
        st.title("Comments", anchor=False)

    def display_header(self, selected_file, selected_version):
        """
        Displays the header with the selected file and version.

        Args:
            selected_file (dict): The selected file dictionary.
            selected_version (dict): The selected version dictionary.
        """
        if selected_file and selected_version:
            # Using markdown for better formatting with smaller text for file and version names
            st.subheader(
                f"Comments for file: **{selected_file['name']}** - "
                f"*Version: {selected_version['name']}*",
                anchor=False,
                divider="violet",
            )

    def show_prepare_download_button(self):
        return st.button(
            "Prepare download",
            help="Prepare the selected version for download",
        )

    def show_download_button(self, file_bytes, file_name, mime_type):
        st.download_button(
            label="Download version",
            data=file_bytes,
            file_name=file_name,  # Ensure this includes .png extension
            mime=mime_type,  # Should be "image/png" for PNG files
            type="primary",
            icon=":material/download:",
            key=f"download_{file_name}",
            help="Download this version of the file",
        )

    def display_searchbar_files(self, placeholder="Search files..."):
        """Displays a searchbar for filtering files by name."""
        search_text = st.text_input(
            label="Search files by name",
            placeholder=placeholder,
            key="search_files",
            help="Search for additional files by name,"
            " if they are not shown in the 10 most recent files",
        )

        return search_text

    def display_version_preview(self, preview_content, file_type):
        """Display a preview of the file version."""
        with st.expander("📄 Version Preview", expanded=True):
            if preview_content is None:
                if file_type == "image":
                    st.warning("Image preview not available")
                else:
                    st.info("Preview not available for this file type")
                return

            if file_type == "image":
                st.image(preview_content)
            else:
                st.info(f"Preview not implemented for {file_type} files")

    def display_selectbox_files(
        self,
        files,
        placeholder="No options",
        label="Select a file:",
    ):
        if not files:
            self._show_message(placeholder, message_type="warning")
            return None

        def format_files(file):
            return format_file_options(file)

        selected_file = st.selectbox(
            label=label,
            options=files,
            format_func=format_files,
            index=0,
            help="Shows the 10 most recently modified files unless searched."
            "Excluding google workspace files like docs, sheets, etc.",
        )

        return selected_file

    def display_selectbox_versions(
        self,
        versions,
        placeholder="No versions found",
        label="Select a version:",
    ):
        if not versions:
            self._show_message(placeholder, message_type="warning")
            return None

        # Format version names with image indicator if applicable
        def format_version(version):
            return version["name"]

        selected_version = st.selectbox(
            label=label,
            options=versions,
            format_func=format_version,
            index=0,
            help="Select a version to preview and comment on",
        )

        return selected_version

    def display_chat_input(self, placeholder="Type your message here..."):
        """Displays a text input box for the user to enter a message."""
        return st.chat_input(placeholder=placeholder)

    def _show_message(self, message, message_type="success"):
        """Displays a message (success, error, or warning)."""
        getattr(st, message_type)(message)

    def display_no_comments_message(self):
        st.markdown(
            """
        <div style='text-align: center; padding: 50px; color: #666;'>
            No comments yet for this version.<br>
            Be the first to add one!
        </div>
        """,
            unsafe_allow_html=True,
        )

    def display_comments_filters(self, comments):
        """
        Displays a container with various comment filtering options.

        Args:
            comments (list): List of all comments to extract filter options from

        Returns:
            dict: Dictionary with filter criteria (status, search_text, user_filter)
        """
        # Initialize default filter criteria
        filter_criteria = {
            "status": "all",
            "search_text": "",
            "user_filter": "all",
        }

        with st.expander("🔍 Filter Comments", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                # Status filter (all/resolved/unresolved)
                status_options = ["all", "resolved", "unresolved"]
                filter_criteria["status"] = st.selectbox(
                    "Status",
                    options=status_options,
                    index=0,
                    key="comment_status_filter",
                    help="Filter comments by status",
                )

            with col2:
                # User filter dropdown
                users = sorted(list({c["user"] for c in comments}))
                user_options = ["all"] + users
                filter_criteria["user_filter"] = st.selectbox(
                    "User",
                    options=user_options,
                    index=0,
                    key="comment_user_filter",
                    help="Filter comments by user",
                )

            with col3:
                # Search by content
                filter_criteria["search_text"] = st.text_input(
                    "Search in comments",
                    value="",  # Explicitly set empty value
                    placeholder="Enter search term...",
                    key="comment_search_filter",
                    help="Search for comments containing this text",
                )

            # Add the apply button centered below the filters
            col_apply, col_clear = st.columns(2)
            with col_apply:
                if st.button(
                    "Apply Filters",
                    use_container_width=True,
                    type="primary",
                    help="Apply selected filters",
                ):
                    return filter_criteria

            with col_clear:
                if st.button(
                    "Clear Filters",
                    use_container_width=True,
                    help="Clear all filters",
                    key="clear_filters_btn",  # Add a unique key
                ):
                    # Return default filter criteria
                    return {
                        "status": "all",
                        "search_text": "",
                        "user_filter": "all",
                    }

        return None

    def display_comment(self, comment):
        """Display a single comment with action buttons and optional replies in a modular way.

        Returns:
            dict or None: Dictionary with action details for either the comment or a reply,
                        None if no action was taken
        """
        # Add one more column for the reply button (now 6 columns total)
        col1, col2, col3, col4, col5, col6 = st.columns([1, 15, 1, 1, 1, 1])

        # Display status indicator
        self._display_status_indicator(col1, comment)

        # Display comment content
        self._display_comment_content(col2, comment)

        action = self._display_action_buttons(col3, col4, col6, col5, comment)

        # Handle replies if they exist
        if replies := comment.get("replies", []):
            with st.expander(f"Replies ({len(replies)})", expanded=False):
                for reply in replies:
                    current_reply_action = self.display_reply(reply)
                    if current_reply_action:
                        action = current_reply_action

        st.divider()

        return action

    def display_reply(self, reply):
        """
        Display a single reply in a clean, indented format with delete option for author.

        Args:
            reply (dict): The reply dictionary containing user, content, timestamp

        Returns:
            dict or None: Dictionary with action details including comment_id if delete action is taken
        """
        # Create columns for layout (icon, content, and action buttons)
        icon_col, content_col, action_col = st.columns([1, 18, 1])

        with icon_col:
            st.markdown("↪️")

        with content_col:
            st.markdown(
                f"""
                <div style='margin-left: 10px; font-size: 0.9em'>
                    <strong>{reply['user']}</strong> <em>(on {reply['timestamp']})</em>
                    <br>
                    {reply['content']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            # Show delete button only if the current user is the author of the reply
            if reply["user"] == self.user_name:
                if st.button(
                    ":material/delete_forever:",
                    key=f"delete_reply_{reply['id']}",
                    help="Delete this reply",
                ):
                    return {
                        "id": reply["id"],
                        "action": "delete_reply",
                    }

        return None

    def _display_status_indicator(self, column, comment):
        """Display the resolved/open status indicator."""
        with column:
            if comment.get("resolved", False):
                st.markdown(
                    "<span style='color: green; font-size: 1.2em'>✓</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span style='color: red; font-size: 1.2em'>●</span>",
                    unsafe_allow_html=True,
                )

    def _display_comment_content(self, column, comment):
        """Display the comment content with metadata."""
        with column:
            status = "Resolved" if comment.get("resolved", False) else "Open"
            status_color = "green" if status == "Resolved" else "red"
            st.markdown(
                f"🗨️ **{comment['user']}** _(on {comment['timestamp']})_ "
                f"<span style='color: {status_color}; font-size: 0.9em'>• {status}</span>"
                f"  \n{comment['content']}",
                unsafe_allow_html=True,
            )

    def _display_action_buttons(
        self,
        edit_col,
        delete_col,
        resolve_col,
        reply_col,
        comment,
    ):
        """Display and handle action buttons (resolve, delete, edit, reply)."""
        action = None

        with edit_col:
            if comment["user"] == self.user_name:
                if st.button(
                    ":material/edit:",
                    key=f"edit_{comment['id']}",
                    help="Edit comment if you are the author",
                ):
                    return {"id": comment["id"], "action": "edit"}

        with delete_col:
            if comment["user"] == self.user_name:
                if st.button(
                    ":material/delete_forever:",
                    key=f"delete_{comment['id']}",
                    help="Delete comment",
                ):
                    return {"id": comment["id"], "action": "delete"}

        with resolve_col:
            action = self._display_resolve_button(comment)
            if action:
                return action

        with reply_col:
            if st.button(
                ":material/reply:",
                key=f"reply_{comment['id']}",
                help="Reply to this comment",
            ):
                return {"id": comment["id"], "action": "reply"}

        return None

    def _display_resolve_button(self, comment):
        """Display and handle resolve/unresolve button."""
        current_status = comment.get("resolved", False)
        button_label = "❌" if current_status else "✅"
        action = "unresolve" if current_status else "resolve"

        if st.button(
            button_label,
            key=f"resolve_btn_{comment['id']}",
            help=f"Mark as {action}",
        ):
            return {"id": comment["id"], "action": action}
        return None

    def display_container(self, height=500, border=False):
        return st.container(height=height, border=border)

    @st.dialog("Edit Comment")
    def display_edit_dialog(
        self, current_content, on_edit_callback, on_cancel_callback
    ):
        """Display a dialog for editing a comment."""
        st.markdown("---")  # Adds a horizontal line for visual separation

        edited_content = st.text_area(
            "Comment content",
            value=current_content,
            height=150,
            key="edit_comment_text_area",
            label_visibility="collapsed",
            placeholder="Type your comment here...",
        )

        st.markdown("")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                ":material/save: Save",
                use_container_width=True,
                type="primary",
            ):
                on_edit_callback(edited_content)
        with col2:
            if st.button(
                ":material/cancel: Cancel",
                use_container_width=True,
            ):
                on_cancel_callback()

    @st.dialog("Reply to Comment")
    def display_reply_dialog(
        self,
        original_comment_content,
        original_author,
        on_reply_callback,
        on_cancel_callback,
    ):
        """Display a dialog for replying to a comment, showing the original comment."""

        # Display the original comment being replied to
        st.markdown("**Replying to:**")
        with st.container(border=True):
            st.markdown(f"**{original_author}:**")
            st.markdown(original_comment_content)

        st.markdown("---")  # Another separator

        reply_content = st.text_area(
            "Your reply",
            height=150,
            key="reply_comment_text_area",
            label_visibility="collapsed",
            placeholder="Type your reply here...",
        )

        st.markdown("")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                ":material/send: Post Reply",
                use_container_width=True,
                type="primary",
            ):
                if (
                    reply_content.strip()
                ):  # Only submit if there's actual content
                    on_reply_callback(reply_content)
        with col2:
            if st.button(
                ":material/cancel: Cancel",
                use_container_width=True,
            ):
                on_cancel_callback()

    @st.dialog("Confirm Deletion")
    def display_delete_confirmation_dialog(
        self,
        content_to_delete,
        on_confirm_callback,
        on_cancel_callback,
        is_reply=False,
    ):
        """Display a confirmation dialog before deletion."""
        st.warning("This action cannot be undone!")

        st.markdown("You are about to delete:")
        with st.container(border=True):
            st.markdown(content_to_delete)

        st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                "Confirm Delete",
                use_container_width=True,
                type="primary",
            ):
                on_confirm_callback()
        with col2:
            if st.button(
                "Cancel",
                use_container_width=True,
            ):
                on_cancel_callback()
