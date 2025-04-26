# blueprint_users.py
from flask import jsonify, Blueprint, request
from anki.collection import Collection

from anki.consts import (
    QUEUE_TYPE_MANUALLY_BURIED,
    QUEUE_TYPE_SIBLING_BURIED,
    QUEUE_TYPE_SUSPENDED,
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_LRN,
    QUEUE_TYPE_REV,
    QUEUE_TYPE_DAY_LEARN_RELEARN,
    QUEUE_TYPE_PREVIEW
)


import os
import shutil

# Map state names to their corresponding queue numbers
state_map = {
        'new': QUEUE_TYPE_NEW,
        'learning': QUEUE_TYPE_LRN,
        'due': QUEUE_TYPE_REV,
        'suspended': QUEUE_TYPE_SUSPENDED,
        'manually_buried': QUEUE_TYPE_MANUALLY_BURIED,
        'sibling_buried': QUEUE_TYPE_SIBLING_BURIED,
        'day_learn_relearn': QUEUE_TYPE_DAY_LEARN_RELEARN,
        'preview': QUEUE_TYPE_PREVIEW
    }

users = Blueprint('users', __name__)

###------------------------- USERS -------------------------###
@users.route('/api/users/create/<username>', methods=['POST'])
def create_user(username):
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    if not os.path.exists(collection_path):
        os.makedirs(os.path.dirname(collection_path), exist_ok=True)
        col = Collection(collection_path)
        col.close()
        return jsonify({"message": f"User {username} created successfully"}), 201
    else:
        return jsonify({"error": "User already exists"}), 400

@users.route('/api/users/delete/<username>', methods=['DELETE'])
def delete_user(username):
    user_dir = os.path.expanduser(f"~/.local/share/Anki2/{username}")
    try:
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            return jsonify({"message": f"User {username} deleted successfully"}), 200
        else:
            return jsonify({"error": "User does not exist"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create an instance of the Syncer class
@users.route('/api/users/sync-login', methods=['POST'])
def sync_login():
    try:
        # Extract parameters from the request
        profile_name = request.json['profile_name']
        username = request.json['username']
        password = request.json['password']
        
        # These parameters are optional with defaults
        upload = request.json.get('upload', False)
        sync_media = request.json.get('sync_media', False)
        endpoint = request.json.get('endpoint')
        
        # Open the collection
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{profile_name}/collection.anki2")
        if not os.path.exists(collection_path):
            return jsonify({"error": f"Profile {profile_name} does not exist"}), 404
            
        col = Collection(collection_path)

        # Step 1: Authenticate with the server
        auth = col.sync_login(username, password, endpoint)
        if not auth or not auth.hkey:
            return jsonify({"error": "Authentication failed"}), 401

        # Step 2: Check sync status first
        sync_status = col.sync_status(auth)
        
        # If the sync status indicates a full sync is required, we need to handle it differently
        if "FULL_SYNC" in str(sync_status):
            # Get the new endpoint if provided
            if hasattr(sync_status, 'new_endpoint') and sync_status.new_endpoint:
                auth.endpoint = sync_status.new_endpoint
            
            # For full sync, skip normal sync and go directly to full_upload_or_download
            full_sync_result = None
            try:
                # Don't pass server_usn for full sync
                col.full_upload_or_download(
                    auth=auth, 
                    server_usn=None, 
                    upload=upload
                )
                full_sync_result = "Full sync completed"
                
                # After full sync, perform media sync if requested
                if sync_media:
                    col.sync_media(auth)
                    media_sync_result = "Media sync completed after full sync"
                else:
                    media_sync_result = "Media sync not requested"
                    
                col.close()
                return jsonify({
                    'hkey': auth.hkey,
                    'endpoint': auth.endpoint,
                    'sync_status': str(sync_status),
                    'full_sync': full_sync_result,
                    'media_sync': media_sync_result
                }), 200
            except Exception as e:
                full_sync_result = f"Full sync error: {str(e)}"
                col.close()
                return jsonify({
                    'hkey': auth.hkey,
                    'endpoint': auth.endpoint,
                    'sync_status': str(sync_status),
                    'error': full_sync_result
                }), 500
        
        # Step 3: Perform normal collection sync if full sync not required
        try:
            sync_output = col.sync_collection(auth=auth, sync_media=False)  # Sync media separately
            server_usn = sync_output.server_media_usn if hasattr(sync_output, 'server_media_usn') else None
        except Exception as e:
            return jsonify({"error": f"Collection sync error: {str(e)}"}), 500

        # Step 4: Handle media sync if requested
        media_sync_result = None
        if sync_media and server_usn is not None:
            try:
                col.sync_media(auth)
                media_sync_result = "Media sync completed"
            except Exception as e:
                media_sync_result = f"Media sync error: {str(e)}"

        # Step 5: Handle full upload/download if requested (should only be needed for normal sync)
        full_sync_result = None
        if upload is not None and server_usn is not None:
            try:
                col.full_upload_or_download(
                    auth=auth, 
                    server_usn=server_usn, 
                    upload=upload
                )
                full_sync_result = "Full sync completed"
            except Exception as e:
                full_sync_result = f"Full sync error: {str(e)}"

        # Close the collection and return the results
        col.close()
        
        return jsonify({
            'hkey': auth.hkey,
            'endpoint': auth.endpoint,
            'sync_status': str(sync_status),
            'sync_output': str(sync_output),
            'media_sync': media_sync_result,
            'full_sync': full_sync_result
        }), 200
        
    except KeyError as e:
        return jsonify({"error": f"Missing required parameter: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error during sync: {str(e)}"}), 500
