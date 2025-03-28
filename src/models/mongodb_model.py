from pymongo.mongo_client import MongoClient
from bson import ObjectId
import streamlit as st

uri = st.secrets["mongodb"]["uri"]
print("Connecting to MongoDB...")
# Create a new client and connect to the server
client = MongoClient(uri)

# Select the database and collection
db = client["google_drive"]
revisions_collection = db["revisions"]
comment_collection = db["comments"]


def mongo_save_version(file_id, version_id, version_name, description):
    """
    Uploads a new version of a file to MongoDB.

    Args:
        file_id (str): The ID of the file.
        version_id (str): The ID of the version.
        version_name (str): The name of the version.
        description (str): The description of the version.
    """
    print("Saving version to MongoDB...")
    query = {"file_id": file_id}
    existing_doc = revisions_collection.find_one(query)

    # Check if the collection already exists

    if existing_doc:
        update = {
            "$setOnInsert": {
                "description": description,
            },
            "$push": {
                "versions": {
                    "id": version_id,
                    "name": version_name,
                    "description": description,
                }
            },
        }
        revisions_collection.update_one(query, update, upsert=True)

    else:
        new_doc = {
            "file_id": file_id,
            "description": description,
            "versions": [
                {
                    "id": version_id,
                    "name": version_name,
                    "description": description,
                }
            ],
        }
        revisions_collection.insert_one(new_doc)


def mongo_delete_version(file_id, version_id):
    """
    Deletes a specific version of a file from MongoDB.

    Args:
        file_id (str): The ID of the file.
        version_id (str): The ID of the version to delete.
    """
    print("Deleting version from MongoDB...")
    query = {"file_id": file_id}

    # Pull the version with the specified version_id from the versions array
    update = {"$pull": {"versions": {"id": version_id}}}

    # Update the document in the collection
    result = revisions_collection.update_one(query, update)

    if result.modified_count > 0:
        print(f"Version with ID {version_id} deleted successfully.")
    else:
        print(f"Version with ID {version_id} not found or already deleted.")


def mongo_get_version(file_id, version_id):
    """
    Retrieves a specific version of a file from MongoDB.

    Args:
        file_id (str): The ID of the file.
        version_id (str): The ID of the version.

    Returns:
        dict or None: The version details if found, otherwise None.
    """
    print("Retrieving version from MongoDB...")
    query = {"file_id": file_id, "versions.id": version_id}
    projection = {"versions.$": 1}  # Only return the matching version

    result = revisions_collection.find_one(query, projection)

    if result and "versions" in result:
        return result["versions"][0]

    return None


def mongo_get_file_description(file_id):
    """
    Retrieves the original description of a file.

    Args:
        file_id (str): The ID of the file.

    Returns:
        str: The original description of the file,
        or None if the file is not found.
    """
    print("Retrieving file description from MongoDB...")
    query = {"file_id": file_id}
    projection = {
        "original_description": 1
    }  # Only return the original_description field

    result = revisions_collection.find_one(query, projection)

    if result and "original_description" in result:
        return result["original_description"]

    return None


def mongo_get_comments_of_version(file_id, version_id):
    """
    Retrieves the comments of a specific version of a file.

    :param file_id: The ID of the file.
    :param version_id: The ID of the version.

    :return: The comments of the version,
    or an empty list if the version or file is not found.
    """
    print("Fetching comments from MongoDB...")
    # Create the query to find the document using the new field names
    query = {"id": file_id, "versions.id": version_id}

    # Find the document in the collection
    existing_doc = comment_collection.find_one(query)

    # If the document exists, retrieve the comments for the specific version
    if existing_doc:
        # Loop through the versions to find the one with the given version_id
        for version in existing_doc["versions"]:
            if version["id"] == version_id:
                return version.get("comments", [])

    # If no document or version found, return an empty list
    return []


def mongo_save_new_comment(
    file_id,
    version_id,
    version_name,
    user,
    timestamp,
    content,
    resolved=False,
):
    """
    Save a new top-level comment to a specific version of a file in MongoDB and return the new comment.
    """
    print("Saving comment to MongoDB...")
    comment_data = {
        "id": str(ObjectId()),
        "user": user,
        "timestamp": timestamp,
        "content": content,
        "resolved": resolved,
        "replies": [],
    }

    query = {"id": file_id, "versions.id": version_id}
    existing_doc = comment_collection.find_one(query)

    if existing_doc:
        # Update existing version with new comment
        update = {"$push": {"versions.$.comments": comment_data}}
        result = comment_collection.update_one(query, update)

        if result.modified_count > 0:
            return comment_data
    else:
        # Check if file exists but version doesn't
        file_exists = comment_collection.find_one({"id": file_id})
        if file_exists:
            # Add new version to existing file
            update = {
                "$push": {
                    "versions": {
                        "id": version_id,
                        "name": version_name,
                        "comments": [comment_data],
                    }
                }
            }
            result = comment_collection.update_one({"id": file_id}, update)
            if result.modified_count > 0:
                return comment_data
        else:
            # Create new document with file, version and comment
            new_doc = {
                "id": file_id,
                "versions": [
                    {
                        "id": version_id,
                        "name": version_name,
                        "comments": [comment_data],
                    }
                ],
            }
            result = comment_collection.insert_one(new_doc)
            if result.inserted_id:
                return comment_data

    return None


def mongo_save_reply(
    file_id, version_id, parent_comment_id, user, timestamp, content
):
    """
    Save a reply to a specific comment in MongoDB and return the new reply.

    Args:
        file_id: ID of the file containing the comment
        version_id: ID of the version containing the comment
        parent_comment_id: ID of the comment being replied to
        user: User information who created the reply
        timestamp: When the reply was created
        content: The reply content

    Returns:
        The reply data if successful, None otherwise
    """
    print("Saving reply to MongoDB...")
    reply_data = {
        "id": str(ObjectId()),
        "user": user,
        "timestamp": timestamp,
        "content": content,
    }

    query = {
        "id": file_id,
        "versions.id": version_id,
        "versions.comments.id": parent_comment_id,
    }

    # This update pushes the reply to the specified comment's replies array
    update = {
        "$push": {
            "versions.$[version].comments.$[comment].replies": reply_data
        }
    }

    array_filters = [
        {"version.id": version_id},
        {"comment.id": parent_comment_id},
    ]

    result = comment_collection.update_one(
        query, update, array_filters=array_filters
    )

    if result.modified_count > 0:
        return reply_data
    return None


def mongo_delete_reply(file_id, version_id, reply_id):
    """
    Delete a specific reply from any comment in MongoDB using just the reply_id.

    Args:
        file_id (str): The ID of the file.
        version_id (str): The ID of the version.
        reply_id (str): The ID of the reply to delete.

    Returns:
        bool: True if the reply was deleted successfully, False otherwise.
    """
    print("Deleting reply from MongoDB...")
    query = {
        "id": file_id,
        "versions.id": version_id,
        "versions.comments.replies.id": reply_id,
    }

    update = {
        "$pull": {"versions.$[version].comments.$[].replies": {"id": reply_id}}
    }

    array_filters = [
        {"version.id": version_id},
    ]

    result = comment_collection.update_one(
        query, update, array_filters=array_filters
    )

    return result.modified_count > 0


def mongo_update_comment_content(file_id, version_id, comment_id, new_content):
    """
    Update the content of a specific comment in MongoDB.
    """
    print("Updating comment content in MongoDB...")
    query = {
        "id": file_id,
        "versions.id": version_id,
        "versions.comments.id": comment_id,
    }
    update = {
        "$set": {
            "versions.$[version].comments.$[comment].content": new_content
        }
    }
    array_filters = [
        {"version.id": version_id},
        {"comment.id": comment_id},
    ]
    result = comment_collection.update_one(
        query, update, array_filters=array_filters
    )
    return result.modified_count > 0


def mongo_delete_comment(file_id, version_id, comment_id):
    """
    Delete a comment from a specific version of a file in MongoDB.
    Uses the new document structure.
    """
    print("Deleting comment from MongoDB...")
    query = {
        "id": file_id,
        "versions.id": version_id,
    }
    update = {"$pull": {"versions.$.comments": {"id": comment_id}}}
    result = comment_collection.update_one(query, update)
    return result.modified_count > 0


def mongo_update_comment_resolved_status(
    file_id, version_id, comment_id, resolved
):
    """
    Update the resolved status of a specific comment in MongoDB.
    Uses the new document structure.
    """
    print("Updating comment resolved status in MongoDB...")
    query = {
        "id": file_id,
        "versions.id": version_id,
        "versions.comments.id": comment_id,
    }
    update = {
        "$set": {"versions.$[version].comments.$[comment].resolved": resolved}
    }
    array_filters = [
        {"version.id": version_id},
        {"comment.id": comment_id},
    ]
    result = comment_collection.update_one(
        query, update, array_filters=array_filters
    )
    return result.modified_count > 0
