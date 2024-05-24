# blueprint_notetypes.py

from flask import jsonify, request, Blueprint
from anki.collection import Collection

from anki.models import NotetypeId, FieldDict

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

notetypes = Blueprint('notetypes_blueprint', __name__)

###------------------------- NOTETYPES -------------------------###
@notetypes.route('/api/notetypes/notes', methods=['GET'])
def get_notetypes():
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        notetypes = col.models.all_names_and_ids()
        col.close()
        return jsonify([{"id": nt.id, "name": nt.name} for nt in notetypes]), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/cards/<int:card_id>/notetype', methods=['GET'])
def get_notetype_id_by_card_id(card_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        card = col.get_card(card_id)
        notetype_id = card.note_type()["id"]
        col.close()
        return jsonify({"notetype_id": notetype_id}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/create-with-fields', methods=['POST'])
def create_notetype_with_fields():
    data = request.json
    notetype_name = data.get('name')
    fields = data.get('fields', [])  # Expecting a list of field names
    base_notetype_id = data.get('base_notetype_id')  # ID of the base notetype to copy the template from
    qfmt = data.get('qfmt')
    afmt = data.get('afmt')
    username = data.get('username')

    if not notetype_name:
        return jsonify({"error": "Notetype name is required"}), 400
    if not fields:
        return jsonify({"error": "At least one field is required"}), 400
    if not base_notetype_id:
        return jsonify({"error": "Base notetype ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Fetch the base notetype to copy the template from
        new_notetype = col.models.new(notetype_name)
        new_template = col.models.new_template(notetype_name)
        
        # Set default qfmt and afmt with the first field
        if fields:
            first_field = fields[0]
            second_field = fields[1]
            if not qfmt:
                new_template['qfmt'] = f"{{{{{first_field}}}}}"
            else:
                new_template['qfmt'] = qfmt
            if not afmt:
                new_template['afmt'] = f"{{{{FrontSide}}}}<hr id=answer>{{{{{second_field}}}}}"
            else:
                new_template['afmt'] = afmt
        
        
        new_notetype['tmpls'] = [new_template]

        for field_name in fields:
            field = FieldDict()
            field['name'] = field_name
            field['ord'] = len(new_notetype['flds'])
            field['sticky'] = False
            field['rtl'] = False
            field['font'] = "Arial"
            field['size'] = 20
            field['media'] = []
            col.models.add_field(new_notetype, field)

        # Save the new notetype
        col.models.add(new_notetype)

        # Commit changes and close the collection
        col.close()

        return jsonify({"message": "Notetype created successfully", "notetype_id": new_notetype['id']}), 201
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/set-sort-field', methods=['POST'])
def set_sort_field(notetype_id):
    data = request.json
    field_name = data.get('field_name')
    username = data.get('username')
    if not field_name or not username:
        return jsonify({"error": "Field name and username are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Find the field index
        field_index = next((idx for idx, fld in enumerate(notetype['flds']) if fld['name'] == field_name), None)
        if field_index is None:
            col.close()
            return jsonify({"error": "Field not found"}), 404

        # Set the sort field
        notetype['sortf'] = field_index
        col.models.save(notetype)
        col.close()

        return jsonify({"message": f"Sort field set to '{field_name}'"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500


@notetypes.route('/api/notetypes/<notetype_id>/reorder-fields', methods=['POST'])
def reorder_fields(notetype_id):
    data = request.json
    new_order = data.get('new_order')  # Dictionary with field names as keys and new order as values
    username = data.get('username')

    if not new_order or not username:
        return jsonify({"error": "New order of fields is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Verify that the new order has the same number of fields
        if len(new_order) != len(notetype['flds']):
            col.close()
            return jsonify({"error": "Mismatch in number of fields"}), 400

        # Reorder fields according to new_order
        current_fields = {field['name']: field for field in notetype['flds']}
        reordered_fields = [None] * len(new_order)

        for field_name, new_ord in new_order.items():
            if field_name in current_fields:
                field = current_fields[field_name]
                field['ord'] = new_ord
                reordered_fields[new_ord] = field
            else:
                col.close()
                return jsonify({"error": f"Field '{field_name}' not found in notetype"}), 404

        # Ensure no None values in reordered_fields
        if None in reordered_fields:
            col.close()
            return jsonify({"error": "Invalid field order provided"}), 400

        notetype['flds'] = reordered_fields
        col.models.save(notetype)
        col.close()

        return jsonify({"message": "Fields reordered successfully"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/add-template', methods=['POST'])
def add_template_to_notetype(notetype_id):
    data = request.json
    template_name = data.get('template_name')
    qfmt = data.get('qfmt')
    afmt = data.get('afmt')
    username = data.get('username')

    if not template_name or not qfmt or not afmt or not username:
        return jsonify({"error": "template_name, qfmt, and afmt are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Create a new template
        template = col.models.new_template(template_name)
        template['qfmt'] = qfmt  # Question format (HTML)
        template['afmt'] = afmt  # Answer format (HTML)
        col.models.add_template(notetype, template)

        # Save the updated notetype
        col.models.save(notetype)
        col.close()

        return jsonify({"message": "Template added successfully"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/update-css', methods=['POST'])
def update_notetype_css(notetype_id):
    data = request.json
    new_css = data.get('css')
    username = data.get('username')
    
    if not new_css:
        return jsonify({"error": "CSS content is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Update the CSS
        notetype['css'] = new_css

        # Save the updated notetype
        col.models.save(notetype)
        col.close()

        return jsonify({"message": "CSS updated successfully"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/fields', methods=['POST'])
def add_field_to_notetype(notetype_id):
    data = request.json
    field_name = data.get('field_name')
    username = data.get('username')

    if not field_name or not username:
        return jsonify({"error": "Field name is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    new_field = FieldDict()

    try:
        notetype = col.models.get(NotetypeId(int(notetype_id)))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Create a new field dictionary
        new_field['name'] = field_name
        new_field['ord'] = len(notetype['flds'])
        new_field['sticky'] = False
        new_field['rtl'] = False
        new_field['font'] = "Arial"
        new_field['size'] = 20
        new_field['media'] = []
        new_field['rtl'] = False
        new_field['sticky'] = False

        # Add the new field
        col.models.add_field(notetype, new_field)
        col.models.save(notetype)
        col.close()
        return jsonify({"message": f"Field '{field_name}' added to notetype {notetype_id}"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500


@notetypes.route('/api/notetypes/<notetype_id>/css', methods=['GET'])
def get_notetype_css(notetype_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        css = notetype.get('css', '')
        col.close()
        return jsonify({"css": css}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/templates', methods=['GET'])
def get_notetype_templates(notetype_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        templates = notetype.get('tmpls', [])
        col.close()
        return jsonify({"templates": templates}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/fields', methods=['GET'])
def get_notetype_fields(notetype_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        fields = notetype.get('flds', [])
        col.close()
        return jsonify({"fields": fields}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/get-sort-field', methods=['GET'])
def get_sort_field(notetype_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        sort_field_index = notetype['sortf']
        sort_field_name = notetype['flds'][sort_field_index]['name'] if sort_field_index < len(notetype['flds']) else None

        col.close()
        return jsonify({"sort_field": sort_field_name}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/fields/<field_name>', methods=['DELETE'])
def remove_field_from_notetype(notetype_id, field_name):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype = col.models.get(NotetypeId(int(notetype_id)))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Find the field to remove
        field_to_remove = None
        for field in notetype['flds']:
            if field['name'] == field_name:
                field_to_remove = field
                break

        if not field_to_remove:
            col.close()
            return jsonify({"error": "Field not found"}), 404

        # Remove the field
        col.models.remove_field(notetype, field_to_remove)
        col.models.save(notetype)
        col.close()
        return jsonify({"message": f"Field '{field_name}' removed from notetype {notetype_id}"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@notetypes.route('/api/notetypes/<notetype_id>/delete', methods=['DELETE'])
def delete_notetype(notetype_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype_id = int(notetype_id)  # Ensure the ID is an integer
        notetype = col.models.get(NotetypeId(notetype_id))
        if not notetype:
            col.close()
            return jsonify({"error": "Notetype not found"}), 404

        # Perform the deletion
        col.models.remove(NotetypeId(notetype_id))
        col.close()
        return jsonify({"message": f"Notetype {notetype_id} deleted successfully"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid notetype ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500