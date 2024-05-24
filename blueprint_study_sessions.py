from flask import jsonify, request, Blueprint
from anki.collection import  Collection
from anki.notes import NoteId

from anki.scheduler.v3 import Scheduler as V3Scheduler
from anki import scheduler_pb2
import os

study_sessions = Blueprint('study_sessions', __name__)

collection_path = None
collection = None
scheduler = None
current_card = None

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


@study_sessions.route('/api/study', methods=['POST'])
def study():
    global collection, scheduler, current_card, collection_path

    data = request.json
    action = data.get('action')
    deck_id = data.get('deck_id')
    username = data.get('username')

    if action == 'start':
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
            queued_cards = scheduler.get_queued_cards(fetch_limit=1)
        except Exception as e:
            return jsonify({"error": f"Error getting queued cards: {e}"}), 500
        if not queued_cards.cards:
            return jsonify({"message": "No more cards to review."}), 200
        try:
            current_card = queued_cards.cards[0]
        except Exception as e:
            return jsonify({"error": f"Error getting current card: {e}"}), 500
        try:
            note = collection.get_note(NoteId(current_card.card.note_id))
        except Exception as e:
            return jsonify({"error": f"Error getting note: {e}"}), 500
        try:
            notetype = collection.models.get(note.mid)
        except Exception as e:
            return jsonify({"error": f"Error getting notetype: {e}"}), 500
        try:
            template = notetype['tmpls'][0]  # Get the template for the card's ordinal
        except Exception as e:
            return jsonify({"error": f"Error getting template: {e}"}), 500
        try:
            front_template = template['qfmt']  # Get the front template HTML
        except Exception as e:
            return jsonify({"error": f"Error getting front template: {e}"}), 500

        try:
            current_card = collection.get_card(current_card.card.id)
        except Exception as e:
            return jsonify({"error": f"Error getting card: {e}"}), 500
        try:
            current_card.start_timer()
        except Exception as e:
            return jsonify({"error": f"Error starting timer: {e}"}), 500
        # Extract fields used in the front template
        try:
            fields_data = {}
            for field_name in note.keys():
                if "{{" + field_name + "}}" in front_template:
                    fields_data[field_name] = note[field_name]
        except Exception as e:
            return jsonify({"error": f"Error extracting fields: {e}"}), 500

        try:
            return jsonify({"front": fields_data, "card_id": current_card.id}), 200
        except Exception as e:
            return jsonify({"error": f"Error returning response: {e}"}), 500

    elif action == 'flip':
        if current_card is None:
            return jsonify({"error": "No card to flip."}), 400
        note = collection.get_note(NoteId(current_card.nid))
        notetype = collection.models.get(note.mid)
        template = notetype['tmpls'][0]  # Get the template for the card's ordinal
        back_template = template['afmt']  # Get the back template HTML

        # Extract fields used in the back template
        fields_data = {}
        for field_name in note.keys():
            if "{{" + field_name + "}}" in back_template:
                fields_data[field_name] = note[field_name]

        return jsonify({"back": fields_data}), 200

    elif action in ['1', '2', '3', '4']:
        if current_card is None:
            return jsonify({"error": "No card to answer."}), 400
        ease = int(action)
        
        # Fetch the current scheduling states for the card
        card_id = current_card.id
        states = scheduler.col._backend.get_scheduling_states(card_id)
        if current_card.timer_started is None:
            #current_card.timer_started = int(time.time() - 1000)
            current_card.start_timer()
        
        # Determine the rating based on the action
        if ease == 1:
            rating = scheduler_pb2.CardAnswer.AGAIN
        elif ease == 2:
            rating = scheduler_pb2.CardAnswer.HARD
        elif ease == 3:
            rating = scheduler_pb2.CardAnswer.GOOD
        elif ease == 4:
            rating = scheduler_pb2.CardAnswer.EASY
        else:
            return jsonify({"error": "Invalid action."}), 400
        
        # Build the CardAnswer object
        try:
            card_answer = scheduler.build_answer(card=current_card, states=states, rating=rating)
        except Exception as e:
            return jsonify({"error": f"current_card.timestarted: {current_card.time_started}, card_id: {current_card.id}, states: {states}, rating: {rating}, error: {e}"}), 500
        
        # Answer the card
        scheduler.answer_card(card_answer)
        
        # Save the collection
        collection.save()
        
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

        fields_data = {}
        for field_name in note.keys():
            if "{{" + field_name + "}}" in front_template:
                fields_data[field_name] = note[field_name]
        return jsonify({"front": fields_data, "card_id": current_card.id, "time_taken_last_card": current_card.time_taken(capped=False)}), 200

    elif action == 'close':
        if collection is not None:
            collection.close()
            collection = None
            scheduler = None
            current_card = None
        return jsonify({"message": "Collection closed."}), 200

    else:
        return jsonify({"error": "Invalid action."}), 400

@study_sessions.route('/api/custom_study', methods=['POST'])
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
    except Exception as e:
        return jsonify({"error": f"Error creating custom study session: {e}"}), 500

    return jsonify({"message": "Custom study session created successfully.", "changes": changes}), 200