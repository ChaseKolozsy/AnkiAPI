from flask import Blueprint, jsonify, request
from anki.collection import (
    Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions,
    ImportCsvRequest, CsvMetadata 
)
from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition

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
delimiter_dict = {
    0: "\t",
    1: "|",
    2: ";",
    3: ":",
    4: ",",
    5: " "
 }

imports = Blueprint('imports', __name__)

###------------------------- IMPORT -------------------------###
@imports.route('/api/import-package', methods=['POST'])
def import_package():
    username = request.args.get('username')  # Assuming username is passed as a query parameter
    if not username:
        return jsonify({"error": "Username is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    temp_file_dir = os.path.expanduser(f"~/temp")
    os.makedirs(temp_file_dir, exist_ok=True)

    if not os.path.exists(temp_file_dir):
        return jsonify({"error": "Failed to create temp dir"}), 500

    try:
        # Save the uploaded file temporarily
        temp_file_path = os.path.join(temp_file_dir, file.filename)
        file.save(temp_file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Verify file was written
    if not os.path.exists(temp_file_path):
        return jsonify({"error": "Failed to save the file"}), 500
    if os.path.getsize(temp_file_path) == 0:
        return jsonify({"error": "Saved file is empty"}), 500

    try:
        # Prepare the import request
        options = ImportAnkiPackageOptions(
            merge_notetypes=True,
            update_notes=ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
            update_notetypes=ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS,
            with_scheduling=True,
            with_deck_configs=True
        )

        import_request = ImportAnkiPackageRequest()
        import_request.package_path = temp_file_path
        import_request.options.CopyFrom(options)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ## Perform the import
    try:
        import_log = col.import_anki_package(import_request)
        os.remove(temp_file_path)  # Clean up the temporary file
        return jsonify({"message": "Package imported successfully"}), 200
    except Exception as e:
        os.remove(temp_file_path)  # Ensure temporary file is cleaned up on failure
        return jsonify({"error": str(e)}), 500

@imports.route('/api/import-csv', methods=['POST'])
def import_csv():
    username = request.args.get('username')
    target_deck_name = request.args.get('target_deck')  # Assume this is also passed in

    if not username or not target_deck_name:
        return jsonify({"error": "Username and target deck name are required"}), 400

    notetype_name = request.args.get('notetype')
    delimiter = request.args.get('delimiter', 'COMMA')
    delimiter_enum = CsvMetadata.Delimiter.Value(delimiter.upper())

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    if not notetype_name or not target_deck_name:
        col.close()
        return jsonify({"error": "Notetype and deck are required"}), 400

    notetype = col.models.by_name(notetype_name)
    if not notetype:
        col.close()
        return jsonify({"error": "Invalid notetype name"}), 400

    target_deck_id = col.decks.id_for_name(target_deck_name)
    if not target_deck_id:
        col.close()
        return jsonify({"error": "Invalid deck name"}), 400

    if 'file' not in request.files:
        col.close()
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        col.close()
        return jsonify({"error": "No selected file"}), 400

    temp_file_dir = os.path.expanduser(f"~/temp")
    os.makedirs(temp_file_dir, exist_ok=True)

    if not os.path.exists(temp_file_dir):
        col.close()
        return jsonify({"error": "Failed to create temp dir"}), 500


    try:
        # Save the uploaded file temporarily
        temp_file_path = os.path.join(temp_file_dir, file.filename)
        file.save(temp_file_path)
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

    # Verify file was written
    if not os.path.exists(temp_file_path):
        col.close()
        return jsonify({"error": "Failed to save the file"}), 500
    if os.path.getsize(temp_file_path) == 0:
        col.close()
        return jsonify({"error": "Saved file is empty"}), 500

    try:
        # Detect delimiter and metadata
        metadata = col.get_csv_metadata(temp_file_path, None)
        
        # Set the notetype and deck for the import
        metadata.global_notetype.id = notetype['id']
        metadata.delimiter = delimiter_enum

        # Determine the number of columns in the CSV file
        with open(temp_file_path, 'r') as f:
            first_line = f.readline()
            num_columns = len(first_line.split(delimiter_dict[delimiter_enum]))

        # Set the tags column to the last column
        metadata.tags_column = num_columns

        # Prepare the import request
        import_request = ImportCsvRequest()
        import_request.path = temp_file_path
        import_request.metadata.CopyFrom(metadata)
    except Exception as e:
        return jsonify({"error": f"{str(e)}"}), 500

    ## Perform the import
    try:
        import_log = col.import_csv(import_request)
        os.remove(temp_file_path)  # Clean up the temporary file

        # Get the ID of the "Default" deck
        default_deck_id = col.decks.id_for_name("Default")
        if not default_deck_id:
            return jsonify({"error": "Default deck not found"}), 404

        # Retrieve all card IDs from the "Default" deck
        default_deck_card_ids = col.decks.cids(default_deck_id)

        # Move the cards to the target deck
        col.set_deck(default_deck_card_ids, target_deck_id)
        col.close()

        return jsonify({"message": "CSV imported and cards moved successfully"}), 200
    except Exception as e:
        os.remove(temp_file_path)  # Ensure temporary file is cleaned up on failure
        col.close()
        return jsonify({"error": str(e)}), 500


@imports.route('/api/unzip-media', methods=['POST'])
def unzip_media():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    media_dir = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.media")
    os.makedirs(media_dir, exist_ok=True)

    temp_file_dir = os.path.expanduser(f"~/temp")
    os.makedirs(temp_file_dir, exist_ok=True)

    try:
        # Save the uploaded zip file temporarily
        temp_zip_path = os.path.join(temp_file_dir, file.filename)
        file.save(temp_zip_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Verify zip file was written
    if not os.path.exists(temp_zip_path):
        return jsonify({"error": "Failed to save the zip file"}), 500
    if os.path.getsize(temp_zip_path) == 0:
        return jsonify({"error": "Saved zip file is empty"}), 500

    try:
        # Unzip the file into the media directory
        import zipfile
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(media_dir)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(temp_zip_path)  # Clean up the temporary file

    return jsonify({"message": "Media unzipped successfully"}), 200

@imports.route('/api/import-media', methods=['POST'])
def import_media():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    media_dir = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.media")
    os.makedirs(media_dir, exist_ok=True)

    media_file_path = os.path.join(media_dir, file.filename)

    try:
        # Save the file directly into the media directory
        file.save(media_file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Verify file was written
    if not os.path.exists(media_file_path):
        return jsonify({"error": "Failed to save the file"}), 500
    if os.path.getsize(media_file_path) == 0:
        return jsonify({"error": "Saved file is empty"}), 500

    return jsonify({"message": "Media file saved successfully"}), 200