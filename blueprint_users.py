# blueprint_users.py
from flask import jsonify, Blueprint
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