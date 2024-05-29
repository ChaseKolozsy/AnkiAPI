# blueprint_export.py
from flask import jsonify, request, Blueprint, send_file
from anki.collection import Collection, ExportAnkiPackageOptions, ExportLimit, DeckIdLimit

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


@exports.route('/api/export-collection-package', methods=['POST'])
def export_collection_package():
    data = request.json
    include_media = data.get('include_media', None)
    legacy = data.get('legacy', None)
    username = request.args.get('username')  

    if type(include_media) == str:
        if include_media.lower() == 'true':
            include_media = True
        else:
            include_media = False
    
    if type(legacy) == str:
        if legacy.lower() == 'true':
            legacy = True
        else:
            legacy = False

    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    out_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.apkg")
    col = Collection(path=collection_path)  # Adjust path as necessary
    try:
        col.export_collection_package(out_path=out_path, include_media=include_media, legacy=legacy)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    
    try:
        return send_file(out_path, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve file: {str(e)}"})

@exports.route('/api/export-anki-package', methods=['POST'])
def export_anki_package():
    out_path = request.args.get('out_path')
    username = request.args.get('username')  
    deck_id = int(request.args.get('deck_id'))
    options = ExportAnkiPackageOptions()
    try:
        deck_id_limit = DeckIdLimit(deck_id=deck_id)
        export_limit: ExportLimit = deck_id_limit
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to create deck id limit: {str(e)}"})

    try:
        options.with_scheduling = True
        options.with_media = True
        options.with_deck_configs = True
        options.legacy = True
    except Exception as e:
        return jsonify({"success": False, "message": f"failed to create export options: {str(e)}"})
    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    
    col = Collection(path=collection_path)  # Adjust path as necessary
    try:
        col.export_anki_package(out_path=out_path, options=options, limit=export_limit)
    except Exception as e:
        return jsonify({"success": False, "message": f"failed to export anki package: {str(e)}, options: {options}, limit: {export_limit}"})

    try:
        return send_file(out_path, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve file: {str(e)}"})

@exports.route('/api/export-note-csv', methods=['POST'])
def export_note_csv():
    out_path = request.args.get('out_path')
    with_html = request.args.get('with_html', False)
    username = request.args.get('username')  
    deck_id = int(request.args.get('deck_id'))
    with_tags = True
    with_deck = False
    with_notetype = False
    with_guid = False
    if with_html == 'True':
        with_html = True
    else:
        with_html = False

    deck_id_limit = DeckIdLimit(deck_id=int(deck_id))
    export_limit: ExportLimit = deck_id_limit
    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    
    col = Collection(path=collection_path)  # Adjust path as necessary
    try:
        col.export_note_csv(out_path=out_path, with_html=with_html, with_tags=with_tags, with_deck=with_deck, with_notetype=with_notetype, with_guid=with_guid, limit=export_limit)
    except Exception as e:
        return jsonify({"success": False, "message": f"failed to export note csv: {str(e)}, out_path: {out_path}, {type(out_path)}, with_html: {with_html, {type(with_html)}}, with_tags: {with_tags}, {type(with_tags)}, with_deck: {with_deck}, {type(with_deck)}, with_notetype: {with_notetype}, {type(with_notetype)}, with_guid: {with_guid}, {type(with_guid)}, limit: {export_limit}, {type(export_limit)}, deck_id: {deck_id}, {type(deck_id)}"})

    try:
        return send_file(out_path, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve file: {str(e)}"})