from flask import jsonify, Blueprint, request
from anki.collection import Collection

from anki.sync_pb2 import SyncAuth

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

db = Blueprint('db', __name__)

###------------------------- DB -------------------------###
# Add the following endpoint to the 'db' blueprint in blueprint_db.py
@db.route('/api/db/sync', methods=['POST'])
def sync_database():
    username = request.json['username']
    endpoint = request.json['endpoint']
    hkey = request.json['hkey']
    sync_media = request.json.get('sync_media', False)
    # Add upload parameter with default value of False
    upload = request.json.get('upload', False)

    try:
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
        col = Collection(collection_path)
    except Exception as e:
        return jsonify({"error": "error opening collection: " + str(e)}), 500

    try:
        # Create auth object
        auth = SyncAuth(endpoint=endpoint, hkey=hkey)
        
        # First check sync status to determine if full sync is needed
        sync_status = col.sync_status(auth)
        
        # If the sync status indicates a full sync is required, handle it differently
        if "FULL_SYNC" in str(sync_status) or "FULL_UPLOAD" in str(sync_status):
            # Get the new endpoint if provided
            if hasattr(sync_status, 'new_endpoint') and sync_status.new_endpoint:
                auth.endpoint = sync_status.new_endpoint
                
            # Perform full sync
            try:
                # For full sync, we don't pass server_usn
                col.full_upload_or_download(auth=auth, server_usn=None, upload=upload)
                
                # After full sync, sync media if requested
                if sync_media:
                    col.sync_media(auth)
                    
                return jsonify({
                    'sync_output': f"{sync_status}",
                    'full_sync': 'completed',
                    'media_sync': 'completed' if sync_media else 'not requested'
                })
            except Exception as e:
                return jsonify({
                    'error': f"Full sync failed: {str(e)}",
                    'sync_status': f"{sync_status}"
                }), 500
        
        # For normal sync
        sync_output = col.sync_collection(auth=auth, sync_media=False)
        
        # For media sync
        media_result = None
        if sync_media:
            server_usn = sync_output.server_media_usn if hasattr(sync_output, 'server_media_usn') else None
            if server_usn is not None:
                col.sync_media(auth)
                media_result = "completed"
        
        return jsonify({
            'sync_output': f"{sync_output}",
            'media_sync': media_result
        })
    except Exception as e:
        return jsonify({'error': f"Error syncing database: {str(e)}"}), 500

# Add the following endpoints to the 'db' blueprint in blueprint_db.py

@db.route('/api/db/sync_status', methods=['POST'])
def sync_status():
    username = request.json['username']
    endpoint = request.json['endpoint']
    hkey = request.json['hkey']

    try:
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
        col = Collection(collection_path)
    except Exception as e:
        return jsonify({"error": "error opening collection: " + str(e)}), 500

    try:
        auth = SyncAuth(endpoint=endpoint, hkey=hkey)
        sync_status = col.sync_status(auth)
        return jsonify({'sync_status': f"{sync_status}"})
    except Exception as e:
        return jsonify({'error': "error getting sync status: " + str(e)}), 500

@db.route('/api/db/media_sync_status', methods=['POST'])
def media_sync_status():
    username = request.json['username']

    try:
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
        col = Collection(collection_path)
    except Exception as e:
        return jsonify({"error": "error opening collection: " + str(e)}), 500

    try:
        media_sync_status = col.media_sync_status()
        return jsonify({'media_sync_status': f"{media_sync_status}"})
    except Exception as e:
        return jsonify({'error': "error getting media sync status: " + str(e)}), 500
