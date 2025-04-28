from flask import jsonify, request, Blueprint
from anki.collection import  Collection
from anki.notes import NoteId

from anki.scheduler.v3 import Scheduler as V3Scheduler
from anki.decks import DeckId
from anki.cards import CardId
from anki import scheduler_pb2
import os
import re
import base64

study_sessions = Blueprint('study_sessions', __name__)

collection_path = None
collection = None
scheduler = None
current_card = None
media_path = None
sound_pattern = re.compile(r'\[sound:(.*?)\]')
img_pattern = re.compile(r'<img src="(.*?)"')

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


### --------------------- Helper Functions ---------------------###
def extract_media_filenames(field_value):
    media_files = []
    start = 0
    while True:
        start_sound = field_value.find('[sound:', start)
        if start_sound == -1:
            break
        start = start_sound + len('[sound:')
        end = field_value.find(']', start)
        if end == -1:
            break
        filename = field_value[start:end].strip()
        media_files.append(filename)
        start = end + 1

    start = 0
    while True:
        start_img = field_value.find('<img src="', start)
        if start_img == -1:
            break
        start = start_img + len('<img src="')
        end = field_value.find('"', start)
        if end == -1:
            break
        filename = field_value[start:end].strip()
        media_files.append(filename)
        start = end + 1

    return media_files

def process_media_files(fields_data, media_path):
    media_files = {}
    for field_name, field_value in fields_data.items():
        filenames = extract_media_filenames(field_value)
        for filename in filenames:
            media_file_path = os.path.join(media_path, filename)
            if os.path.exists(media_file_path):
                with open(media_file_path, 'rb') as media_file:
                    media_files[filename] = base64.b64encode(media_file.read()).decode('utf-8')
    return media_files



### --------------------- STUDY SESSION ---------------------###


@study_sessions.route('/api/study', methods=['POST'])
def study():
    global collection, scheduler, current_card, collection_path, media_path

    data = request.json
    action = data.get('action')
    deck_id = data.get('deck_id')
    username = data.get('username')


    try:
        if action == 'start':
            collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
            media_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.media")
            if collection is None:
                collection = Collection(collection_path)
                scheduler = V3Scheduler(collection)

            collection.decks.select(deck_id)
            queued_cards = scheduler.get_queued_cards(fetch_limit=1)
            if not queued_cards.cards:
                return jsonify({"message": "No more cards to review."}), 200

            current_card = queued_cards.cards[0]
            note = collection.get_note(NoteId(current_card.card.note_id))
            notetype = collection.models.get(note.mid)
            template = notetype['tmpls'][0]  # Get the template for the card's ordinal
            front_template = template['qfmt']  # Get the front template HTML

            current_card = collection.get_card(current_card.card.id)
            current_card.start_timer()

            # Extract fields used in the front template
            fields_data = {field_name: note[field_name] for field_name in note.keys() if "{{" + field_name + "}}" in front_template}

            # Extract fields and media files using the helper function
            media_files = process_media_files(fields_data, media_path)

            return jsonify({"front": fields_data, "card_id": current_card.id, "media_files": media_files}), 200, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

        elif action == 'flip':
            if current_card is None:
                return jsonify({"error": "No card to flip."}), 400

            note = collection.get_note(NoteId(current_card.nid))
            notetype = collection.models.get(note.mid)
            template = notetype['tmpls'][0]  # Get the template for the card's ordinal
            back_template = template['afmt']  # Get the back template HTML

            # Extract fields used in the back template
            fields_data = {field_name: note[field_name] for field_name in note.keys() if "{{" + field_name + "}}" in back_template}
            try:
                ease_enumerations = {1: "1: Again", 2: "2: Hard", 3: "3: Good", 4: "4: Easy" }
                ease_dict = {}
                for i in range(1, 5):
                    ease_dict[ease_enumerations[i]] = scheduler.nextIvlStr(current_card, i)
            except Exception as e:
                return jsonify({"error": f"Error getting ease options: {e}"}), 500

            # Extract fields and media files using the helper function
            media_files = process_media_files(fields_data, media_path)
            return jsonify({"back": fields_data, "ease_options": ease_dict, "media_files": media_files}), 200, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

        elif action in ['1', '2', '3', '4']:
            if current_card is None:
                return jsonify({"error": "No card to answer."}), 400
            ease = int(action)
            # Fetch the current scheduling states for the card
            card_id = current_card.id
            states = scheduler.col._backend.get_scheduling_states(card_id)
            if current_card.timer_started is None:
                current_card.start_timer()

            # Determine the rating based on the action
            rating_map = {
                1: scheduler_pb2.CardAnswer.AGAIN,
                2: scheduler_pb2.CardAnswer.HARD,
                3: scheduler_pb2.CardAnswer.GOOD,
                4: scheduler_pb2.CardAnswer.EASY
            }
            rating = rating_map.get(ease)
            if rating is None:
                return jsonify({"error": "Invalid action."}), 400

            # Build the CardAnswer object
            card_answer = scheduler.build_answer(card=current_card, states=states, rating=rating)
            # Answer the card
            scheduler.answer_card(card_answer)

            # Fetch the next queued card
            queued_cards = scheduler.get_queued_cards(fetch_limit=1)
            if not queued_cards.cards:
                return jsonify({"message": "No more cards to review."}), 200
            current_card = queued_cards.cards[0]
            note = collection.get_note(NoteId(current_card.card.note_id))
            notetype = collection.models.get(note.mid)
            template = notetype['tmpls'][0]  # Get the template for the card's ordinal
            front_template = template['qfmt']

            current_card = collection.get_card(current_card.card.id)
            current_card.start_timer()

            fields_data = {field_name: note[field_name] for field_name in note.keys() if "{{" + field_name + "}}" in front_template}

            # Extract media references
            media_files = process_media_files(fields_data, media_path)

            return jsonify({"front": fields_data, "card_id": current_card.id, "time_taken_last_card": current_card.time_taken(capped=False), "media_files": media_files}), 200, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

        elif action == 'close':
            if collection is not None:
                collection.close()
                collection = None
                scheduler = None
                current_card = None
            return jsonify({"message": "Collection closed."}), 200, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

        else:
            return jsonify({"error": "Invalid action."}), 400, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500, {'Content-Type': 'application/json; charset=utf-8', 'ensure_ascii': False}

@study_sessions.route('/api/custom-study', methods=['POST'])
def custom_study():
    global collection, scheduler, collection_path

    data = request.json
    username = data.get('username')
    deck_id = data.get('deck_id')
    custom_study_params = data.get('custom_study_params')

    try:
        collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
        if collection is None:
            collection = Collection(collection_path)
            scheduler = V3Scheduler(collection)
    except Exception as e:
        return jsonify({"error": f"Error opening collection: {e}, collection_path: {collection_path}"}), 500

    try:
        collection.decks.select(deck_id)
    except Exception as e:
        return jsonify({"error": f"Error selecting deck: {e}"}), 500
    

    try:
        custom_study_request = scheduler_pb2.CustomStudyRequest(
            deck_id=deck_id,
            **custom_study_params
        )
        changes = scheduler.custom_study(custom_study_request)
        custom_defaults = scheduler.custom_study_defaults(DeckId(int(deck_id)))
        collection.close()
    except Exception as e:
        return jsonify({"error": f"Error creating custom study session: {e}"}), 500

    return jsonify({"message": "Custom study session created successfully.", "changes": str(changes), "custom_defaults": str(custom_defaults)}), 200

