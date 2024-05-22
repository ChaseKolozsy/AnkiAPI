# blueprint_export.py
from flask import jsonify, request, Blueprint
from anki.collection import Collection, ExportAnkiPackageOptions

from anki.notes import NoteId

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

exports = Blueprint('exports', __name__)


###--------------------------- EXPORT ----------------------------###

@exports.route('/api/export-package', methods=['GET'])
def export_package():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        export_path = os.path.expanduser(f"~/exports/{username}.apkg")
        options = ExportAnkiPackageOptions(
            include_media=True,
            include_scheduling=True,
            include_deck_configs=True
        )
        col.export_anki_package(export_path, options)
        col.close()
        return jsonify({"message": "Package exported successfully", "path": export_path}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500


@exports.route('/api/export-notes', methods=['GET'])
def export_notes():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notes = col.find_notes("")
        export_path = os.path.expanduser(f"~/exports/{username}_notes.txt")
        with open(export_path, 'w') as f:
            for note_id in notes:
                note = col.get_note(NoteId(note_id))
                f.write(f"Note ID: {note_id}\n")
                for field_name, field_value in note.items():
                    f.write(f"{field_name}: {field_value}\n")
                f.write("\n")
        col.close()
        return jsonify({"message": "Notes exported successfully", "path": export_path}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500