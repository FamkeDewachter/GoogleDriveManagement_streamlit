from datetime import datetime
from dateutil import tz
import streamlit as st
import io
from PIL import Image


def format_folder_options(option):
    """
    Format folder options to display in the selectbox.
    Add indentation based on the depth of the folder.

    Args:
        option (dict): The option to format, containing the name and depth.
    Returns:
        str: The formatted folder name with indentation based on depth.
    """
    depth = option.get("depth", 1)  # Default depth is 1 if not provided
    if depth == 0:
        # Bold the name for depth 0
        indentation = ""  # No indentation for depth 0
        formatted_name = f"**{option['name']}**"  # Bold for depth 0
    else:
        indentation = "---" * (depth - 1)  # Add indentation based on depth
        formatted_name = (
            f"{option['name']}"  # Regular formatting for other depths
        )

    return f"{indentation} {formatted_name}"


def format_file_options(option):
    """
    Format file options to display in the selectbox.
    Shows the file name followed by the folder name in brackets.

    Args:
        option (dict): The option to format, containing the name and folder_name.
    Returns:
        str: The formatted file name with folder name in brackets.
    """
    file_name = option.get("name", "")
    folder_name = option.get("folder_name", "")

    if folder_name:
        return f"{file_name} ({folder_name})"
    return file_name


def format_mime_type(mime_type):
    mime_type_mapping = {
        # Text & Documents
        "text/plain": "Text File",
        "application/pdf": "PDF Document",
        "application/vnd.google-apps.document": "Google Docs",
        "application/vnd.google-apps.spreadsheet": "Google Sheets",
        # 3D Models
        "model/fbx": "Autodesk FBX Model",
        "model/obj": "Wavefront OBJ Model",
        "model/gltf+json": "GLTF Model",
        "model/gltf-binary": "GLB Model",
        "application/x-blender": "Blender Project",
        "application/x-3dsmax": "3ds Max File",
        "application/x-maya": "Maya File",
        "model/stl": "STL 3D Model",
        "model/ply": "PLY 3D Model",
        # Textures & Images
        "image/png": "PNG Image",
        "image/jpeg": "JPEG Image",
        "image/x-targa": "TGA Texture",
        "image/vnd-ms.dds": "DDS Texture",
        "image/x-exr": "EXR Texture",
        "image/bmp": "BMP Image",
        "image/vnd.adobe.photoshop": "Photoshop PSD",
        "image/vnd.radiance": "HDR Image",
        # Audio
        "audio/wav": "WAV Audio",
        "audio/mpeg": "MP3 Audio",
        "audio/ogg": "OGG Audio",
        "audio/flac": "FLAC Audio",
        # Video
        "video/mp4": "MP4 Video",
        "video/quicktime": "MOV Video",
        "video/x-msvideo": "AVI Video",
        "video/webm": "WebM Video",
        # Scripts & Code
        "text/x-python": "Python Script",
        "text/x-csharp": "C# Script",
        "text/x-c++src": "C++ Source File",
        "text/x-c++hdr": "C++ Header File",
        "text/x-lua": "Lua Script",
        "application/json": "JSON File",
        "application/xml": "XML File",
        # Game Engine Files
        "application/vnd.unity": "Unity Scene",
        "application/vnd.unreal": "Unreal Asset",
        "application/vnd.unreal-project": "Unreal Project",
    }

    return mime_type_mapping.get(mime_type, "Unknown File Type")


def format_size(size_in_bytes):
    """
    Convert size in bytes to a human-readable format (e.g., KB, MB, GB, TB).

    Args:
        size_in_bytes (int or str): The size in bytes.

    Returns:
        str: The formatted size string.
    """
    # Convert size_in_bytes to an integer if it's a string
    if isinstance(size_in_bytes, str):
        try:
            size_in_bytes = int(size_in_bytes)
        except ValueError:
            return "N/A"

    # Define the size units
    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    # Handle invalid or zero sizes
    if size_in_bytes <= 0:
        return "0 B"

    # Calculate the appropriate unit
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1

    # Format the size to 2 decimal places
    return f"{size_in_bytes:.2f} {units[unit_index]}"


def format_date(date_input):
    """
    Convert an ISO 8601 date string or
    datetime.datetime object to a human-readable format.

    Args:
        date_input (str or datetime.datetime): The date input,
            either as an ISO 8601 string
            (e.g., "2025-03-16T19:07:00.800Z") or a datetime.datetime object.

    Returns:
        str: The formatted date string (e.g., "2025-03-16 19:07:00").
            Returns "N/A" if the input is invalid or cannot be parsed.
    """
    try:
        # If the input is already a datetime object, format it directly
        if isinstance(date_input, datetime):
            return date_input.strftime("%Y-%m-%d %H:%M:%S")

        # If the input is a string, parse it as an ISO 8601 date
        elif isinstance(date_input, str):
            # Parse the date as UTC
            dt = datetime.fromisoformat(date_input.replace("Z", "+00:00"))
            # Convert to local time zone
            dt = dt.replace(tzinfo=tz.UTC).astimezone(tz.tzlocal())
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        # If the input is neither a string nor a datetime object, return "N/A"
        else:
            return "N/A"

    except ValueError:
        return "N/A"
