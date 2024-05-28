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

    try:
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
        col = Collection(collection_path)
    except Exception as e:
        return jsonify({"error": "error opening collection: " + str(e)}), 500

    try:
        # Assuming the collection is already logged in the Anki backend
        auth = SyncAuth(endpoint=endpoint, hkey=hkey)
        sync_output = col.sync_collection(auth=auth, sync_media=False)
        return jsonify({'sync_output': f"{sync_output}"})
    except Exception as e:
        return jsonify({'error': "error syncing database: " + str(e)}), 500
