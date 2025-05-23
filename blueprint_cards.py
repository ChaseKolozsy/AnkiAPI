# blueprint_cards.py
from flask import jsonify, request, Blueprint
from anki.collection import  Collection

from anki.models import NotetypeId, ChangeNotetypeRequest, ModelManager
from anki.notes import NoteId
from anki.cards import CardQueue


from anki.decks import DeckId
from anki.cards import CardId

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

cards = Blueprint('cards', __name__)

###----------------------- HELPERS -----------------------###
def change_notetype(col, note_id, new_notetype_id, match_by_name):
    try:
        card_id = col.card_ids_of_note(note_id)[0]
        new_notetype_id = int(new_notetype_id)
        card = col.get_card(CardId(card_id))
        old_notetype_id = card.note_type()["id"]
        current_schema = col.db.scalar("select scm from col")

        # Fetch field names and 'ord' values for both notetypes
        old_notetype = col.models.get(NotetypeId(old_notetype_id))
        new_notetype = col.models.get(NotetypeId(new_notetype_id))
        old_fields = old_notetype['flds']
        new_fields = new_notetype['flds']

        # Create field mapping based on 'match_by_name' variable
        field_mapping = []
        if match_by_name:
            old_field_names = [field['name'] for field in old_fields]
            new_field_names = [field['name'] for field in new_fields]
            for old_field in old_field_names:
                if old_field in new_field_names:
                    field_mapping.append(new_field_names.index(old_field))
                else:
                    field_mapping.append(-1)  # Field does not exist in new notetype
        else:
            for old_field in old_fields:
                matching_field = next((f for f in new_fields if f['ord'] == old_field['ord']), None)
                if matching_field:
                    field_mapping.append(matching_field['ord'])
                else:
                    field_mapping.append(-1)  # Field does not exist in new notetype

        # Prepare the change notetype request
        change_request = ChangeNotetypeRequest()
        change_request.note_ids.extend([note_id])
        change_request.old_notetype_id = old_notetype_id
        change_request.new_notetype_id = new_notetype_id
        change_request.current_schema = current_schema
        change_request.new_fields.extend(field_mapping)

        # Execute the change notetype operation
        col.models.change_notetype_of_notes(change_request)
    except Exception as e:
        raise Exception(f"error in change notetype request: {str(e)}")

###------------------------- CARDS -------------------------###
@cards.route('/api/cards/create', methods=['POST'])
def create_card():
    data = request.json
    username = data.get('username')
    note_type = data.get('note_type')
    deck_id = data.get('deck_id')
    fields = data.get('fields')
    tags = data.get('tags', [])

    if not note_type or not deck_id or not fields:
        return jsonify({"error": "note_type, deck_id, and fields are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        notetype = col.models.by_name(note_type)
        if not notetype:
            return jsonify({"error": "Invalid note type"}), 400

        note = col.new_note(notetype)
        for field, value in fields.items():
            note[field] = value
        note.tags = tags

        col.add_note(note, DeckId(deck_id))
        card_ids = col.card_ids_of_note(note.id)
        col.close()
        return jsonify({"message": "Card created successfully", "note_id": note.id, "card_ids": card_ids}), 201
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<note_id>/change-notetype', methods=['POST'])
def change_card_notetype(note_id):
    data = request.json
    username = data.get('username')
    new_notetype_id = data.get('new_notetype_id')
    match_by_name = data.get('match_by_name', True)

    if not new_notetype_id:
        return jsonify({"error": "New notetype ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        note_id = int(note_id)
        change_notetype(col, note_id, new_notetype_id, match_by_name)
        col.close()
        return jsonify({"message": "Notetype changed successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500


@cards.route('/api/cards/change-notetype-by-tag', methods=['POST'])
def change_notetype_by_tag():
    data = request.json
    tag = data.get('tag')
    new_notetype_id = data.get('new_notetype_id')
    match_by_name = data.get('match_by_name', True)
    username = data.get('username')

    if not tag or not new_notetype_id:
        return jsonify({"error": "Tag and new notetype ID are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        new_notetype_id = int(new_notetype_id)
        note_ids = col.find_notes(f"tag:{tag}")

        for note_id in note_ids:
            change_notetype(col, note_id, new_notetype_id, match_by_name)

        col.close()
        return jsonify({"message": "Notetypes changed successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/change-notetype-by-current', methods=['POST'])
def change_notetype_by_current():
    data = request.json
    current_notetype_id = data.get('current_notetype_id')
    new_notetype_id = data.get('new_notetype_id')
    match_by_name = data.get('match_by_name', True)
    username = data.get('username')

    if not current_notetype_id or not new_notetype_id:
        return jsonify({"error": "Current and new notetype IDs are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        current_notetype_id = int(current_notetype_id)
        new_notetype_id = int(new_notetype_id)
        note_ids = col.find_notes(f"mid:{current_notetype_id}")

        for note_id in note_ids:
            change_notetype(col, note_id, new_notetype_id, match_by_name)

        col.close()
        return jsonify({"message": "Notetypes changed successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/move-cards', methods=['POST'])
def move_cards():
    data = request.json
    card_ids = data.get('card_ids')
    target_deck_name = data.get('target_deck_name')
    username = data.get('username')

    if not card_ids or not target_deck_name or not username:
        return jsonify({"error": "card_ids, target_deck_name, and username are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Convert card IDs from string to CardId type
        card_ids = [CardId(int(cid)) for cid in card_ids]

        # Get the target deck ID
        target_deck_id = col.decks.id_for_name(target_deck_name)
        if not target_deck_id:
            return jsonify({"error": "Target deck not found"}), 404

        # Move the cards to the target deck
        col.set_deck(card_ids, target_deck_id)
        col.close()
        return jsonify({"message": "Cards moved successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<card_id>/reschedule', methods=['POST'])
def reschedule_card(card_id):
    data = request.json
    new_due_date = data.get('new_due_date')
    username = data.get('username')

    if not new_due_date:
        return jsonify({"error": "New due date is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        card_id = int(card_id)
        col.sched.set_due_date([card_id], str(new_due_date))
        col.close()
        return jsonify({"message": "Card rescheduled successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/reschedule/by-tag', methods=['POST'])
def reschedule_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    new_due_date = data.get('new_due_date')
    start_days = data.get('start_days')
    end_days = data.get('end_days')
    only_if_due = data.get('only_if_due', False)
    username = data.get('username')

    if not tag or (not new_due_date and (start_days is None or end_days is None)):
        return jsonify({"error": "Tag and new due date or start and end days are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        card_ids = []
        cards_to_reschedule = []
        for note_id in note_ids:
            card_ids.extend(col.card_ids_of_note(note_id))
    except Exception as e:
        col.close()
        return jsonify({"error": f"error was in gathering note_ids: {e}"}), 500

    try:
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            if only_if_due and card.queue != CardQueue.DUE:
                continue
            else:
                cards_to_reschedule.append(card_id)
    except Exception as e:
        col.close()
        return jsonify({"error": f"error was in gathering card_ids: {e}"}), 500
    
    try:
        if new_due_date:
            col.sched.set_due_date(cards_to_reschedule, new_due_date)
        else:
            col.sched.set_due_date(cards_to_reschedule, f'{start_days}-{end_days}')

        col.close()
        return jsonify({"message": "Cards rescheduled successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": f"error was in rescheduling cards: {e}"}, {"cards_to_reschedule": str(cards_to_reschedule)}), 500

@cards.route('/api/cards/reschedule/by-deck', methods=['POST'])
def reschedule_cards_by_deck():
    data = request.json
    deck_id = data.get('deck_id')
    new_due_date = data.get('new_due_date')
    start_days = data.get('start_days')
    end_days = data.get('end_days')
    only_if_due = data.get('only_if_due', False)
    username = data.get('username')

    if not deck_id or (not new_due_date and (start_days is None or end_days is None)):
        return jsonify({"error": "Deck ID and new due date or start and end days are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        cards_to_reschedule = []
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            if only_if_due and card.queue != CardQueue.DUE:
                continue
            else:
                cards_to_reschedule.append(card_id)
        
        if new_due_date:
            days = str(new_due_date)
        else:
            days = f'{start_days}-{end_days}'

        # Ensure days is a string
        if not isinstance(days, str):
            raise ValueError("Days parameter must be a string")

        col.sched.set_due_date(cards_to_reschedule, days)

        col.close()
        return jsonify({"message": "Cards rescheduled successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": f"error was in rescheduling cards: {e}, {days}"}), 500

@cards.route('/api/cards/<card_id>/reposition', methods=['POST'])
def reposition_card(card_id):
    data = request.json
    new_position = data.get('new_position')
    increment_collection = data.get('increment_collection', False)
    randomize = data.get('randomize', False)
    username = data.get('username')

    if new_position is None:
        return jsonify({"error": "New position is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        card_id = int(card_id)
        col.sched.reposition_new_cards([card_id], new_position, 1, randomize, increment_collection)
        col.close()
        return jsonify({"message": "Card repositioned successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/reposition/by-tag', methods=['POST'])
def reposition_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    new_position = data.get('new_position')
    increment_collection = data.get('increment_collection', False)
    randomize = data.get('randomize', False)
    username = data.get('username')

    if not tag or new_position is None:
        return jsonify({"error": "Tag and new position are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        card_ids = [card_id for note_id in note_ids for card_id in col.card_ids_of_note(note_id)]
        col.sched.reposition_new_cards(card_ids, new_position, 1, randomize, increment_collection)
        col.close()
        return jsonify({"message": "Cards repositioned successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/reposition/by-deck', methods=['POST'])
def reposition_cards_by_deck():
    data = request.json
    deck_id = data.get('deck_id')
    new_position = data.get('new_position')
    increment_collection = data.get('increment_collection', False)
    randomize = data.get('randomize', False)
    username = data.get('username')

    if not deck_id or new_position is None:
        return jsonify({"error": "Deck ID and new position are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        col.sched.reposition_new_cards(card_ids, new_position, 1, randomize, increment_collection)
        col.close()
        return jsonify({"message": "Cards repositioned successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<card_id>/reset', methods=['POST'])
def reset_card(card_id):
    collection_path = os.path.expanduser("~/.local/share/Anki2/User 1/collection.anki2")
    col = Collection(collection_path)

    try:
        card_id = int(card_id)
        col.sched.schedule_cards_as_new([card_id])
        col.close()
        return jsonify({"message": "Card reset successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/reset/by-tag', methods=['POST'])
def reset_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    username = data.get('username')

    if not tag:
        return jsonify({"error": "Tag is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        cards_to_reset = []
        note_ids = col.find_notes(f"tag:{tag}")
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            cards_to_reset.extend(card_ids)
        col.sched.schedule_cards_as_new(cards_to_reset)
        col.close()
        return jsonify({"message": "Cards reset successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/reset/by-deck', methods=['POST'])
def reset_cards_by_deck():
    data = request.json
    deck_id = data.get('deck_id')
    username = data.get('username')

    if not deck_id:
        return jsonify({"error": "Deck ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        col.sched.schedule_cards_as_new(card_ids)
        col.close()
        return jsonify({"message": "Cards reset successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<card_id>/suspend', methods=['POST'])
def suspend_card(card_id):
    data = request.json
    username = data.get('username')

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        card_id = int(card_id)
        col.sched.suspend_cards([card_id])
        col.close()
        return jsonify({"message": "Card suspended successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/suspend/by-tag', methods=['POST'])
def suspend_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    username = data.get('username')

    if not tag:
        return jsonify({"error": "Tag is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        cards_to_suspend = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            cards_to_suspend.extend(card_ids)
        col.sched.suspend_cards(cards_to_suspend)
        col.close()
        return jsonify({"message": "Cards suspended successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/suspend/by-deck', methods=['POST'])
def suspend_cards_by_deck():
    data = request.json
    deck_id = data.get('deck_id')
    username = data.get('username')

    if not deck_id:
        return jsonify({"error": "Deck ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        col.sched.suspend_cards(card_ids)
        col.close()
        return jsonify({"message": "Cards suspended successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<card_id>/bury', methods=['POST'])
def bury_card(card_id):
    data = request.json
    username = data.get('username')

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        card_id = int(card_id)
        card = col.get_card(CardId(card_id))
        card.queue = QUEUE_TYPE_MANUALLY_BURIED  # Set queue to scheduler buried
        col.update_card(card)  # Save changes
        col.close()
        return jsonify({"message": "Card buried successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/bury/by-tag', methods=['POST'])
def bury_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    username = data.get('username')

    if not tag:
        return jsonify({"error": "Tag is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                card.queue = QUEUE_TYPE_MANUALLY_BURIED  # Set queue to scheduler buried
                col.update_card(card)  # Save changes
        col.close()
        return jsonify({"message": "Cards buried successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/bury/by-deck', methods=['POST'])
def bury_cards_by_deck():
    data = request.json
    deck_id = data.get('deck_id')
    username = data.get('username')

    if not deck_id:
        return jsonify({"error": "Deck ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            card.queue = QUEUE_TYPE_MANUALLY_BURIED  # Set queue to scheduler buried
            col.update_card(card)  # Save changes
        col.close()
        return jsonify({"message": "Cards buried successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<card_id>/contents', methods=['GET'])
def get_card_contents(card_id):
    data = request.json
    username = data.get('username')

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        card_id = int(card_id)
        col = Collection(collection_path)
        card = col.get_card(CardId(card_id))
        if card:
            note = col.get_note(card.nid)
            field_contents = {field_name: note[field_name] for field_name in note.keys()}
            col.close()
            return jsonify({"id": card.id, "note_id": card.nid, "deck_id": card.did, "fields": field_contents})
        else:
            col.close()
            return jsonify({"error": "Card not found"}), 404
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid card ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500


@cards.route('/api/cards/<note_id>', methods=['GET'])
def get_card_by_id(note_id):
    data = request.json
    username = data.get('username')

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        note_id = int(note_id)
        col = Collection(collection_path)
        card = col.get_card(CardId(note_id))
        if card:
            card_detail = {'id': card.id, 'note_id': card.nid, 'deck_id': card.did, 'queue': card.queue}
            col.close()
            return jsonify(card_detail)
        else:
            col.close()
            return jsonify({"error": "Card not found"}), 404
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid card ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-tag', methods=['GET'])
def get_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    username = data.get('username')
    inclusions = data.get('inclusions', None)

    if not tag:
        return jsonify({"error": "Tag is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Find notes with the given tag
        note_ids = col.find_notes(f"tag:{tag}")
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                note = col.get_note(note_id)
                if inclusions is not None:
                    field_contents = {field: note[field] for field in inclusions if field in note.keys()}
                else:
                    field_contents = {field_name: note[field_name] for field_name in note.keys()}
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "fields": field_contents,
                    "queue": card.queue,
                    "due": card.due
                })
        col.close()
        return jsonify(cards), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<deck_id>/by-state', methods=['GET'])
def get_cards_by_state(deck_id):
    data = request.json
    state = data.get('state')
    username = data.get('username')
    inclusions = data.get('inclusions', None)

    if not state:
        return jsonify({"error": "State parameter is required"}), 400


    if state not in state_map:
        return jsonify({"error": "Invalid state"}), 400

    queue_type = state_map[state]

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        # Find cards with the specified state
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        cards = []

        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            note = col.get_note(card.nid)
            if inclusions is not None:
                field_contents = {field: note[field] for field in inclusions if field in note.keys()}
            else:
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
            if card.queue == queue_type:
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "fields": field_contents,
                    "queue": card.queue,
                    "tags": note.tags
                })

        col.close()
        return jsonify(cards), 200
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/<deck_id>/by-state-without-fields', methods=['GET'])
def get_cards_by_state_without_fields(deck_id):
    data = request.json
    state = data.get('state')
    username = data.get('username')

    if not state:
        return jsonify({"error": "State parameter is required"}), 400


    if state not in state_map:
        return jsonify({"error": "Invalid state"}), 400

    queue_type = state_map[state]

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        # Find cards with the specified state
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        cards = []

        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            note = col.get_note(card.nid)
            field_contents = {field_name: note[field_name] for field_name in note.keys()}
            if card.queue == queue_type:
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "queue": card.queue,
                    "tags": note.tags
                })

        col.close()
        return jsonify(cards), 200
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-tag-and-state', methods=['GET'])
def get_cards_by_tag_and_state():
    data = request.json
    tag = data.get('tag')
    state = data.get('state')
    username = data.get('username')
    inclusions = data.get('inclusions', None)

    if not tag or not state:
        return jsonify({"error": "Tag and State parameters are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    if state not in state_map:
        return jsonify({"error": "Invalid state"}), 400

    queue_type = state_map[state]

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                note = col.get_note(note_id)
                if inclusions is not None:
                    field_contents = {field: note[field] for field in inclusions if field in note.keys()}
                else:
                    field_contents = {field_name: note[field_name] for field_name in note.keys()}
                if card.queue == queue_type:
                    cards.append({
                        "id": card.id,
                        "note_id": card.nid,
                        "deck_id": card.did,
                        "fields": field_contents,
                        "queue": card.queue
                    })
        col.close()
        return jsonify(cards), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-tag-and-state-without-fields', methods=['GET'])
def get_cards_by_tag_and_state_without_fields():
    data = request.json
    tag = data.get('tag')
    state = data.get('state')
    username = data.get('username')

    if not tag or not state:
        return jsonify({"error": "Tag and State parameters are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    if state not in state_map:
        return jsonify({"error": "Invalid state"}), 400

    queue_type = state_map[state]

    try:
        note_ids = col.find_notes(f"tag:{tag}")
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                note = col.get_note(note_id)
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
                if card.queue == queue_type:
                    cards.append({
                        "id": card.id,
                        "note_id": card.nid,
                        "deck_id": card.did,
                        "queue": card.queue
                    })
        col.close()
        return jsonify(cards), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/delete/<card_id>', methods=['DELETE'])
def delete_card(card_id):
    data = request.json
    username = data.get('username')


    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        card_id = int(card_id)
        col = Collection(collection_path)
        card = col.get_card(CardId(card_id))
        if card:
            col.remove_notes_by_card([CardId(card_id)])
            col.close()
            return jsonify({"message": f"Card {card_id} deleted successfully"}), 200
        else:
            col.close()
            return jsonify({"error": "Card not found"}), 404
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid card ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/delete/by-tag', methods=['DELETE'])
def delete_cards_by_tag():
    data = request.json
    tag = data.get('tag')
    username = data.get('username')

    if not tag:
        return jsonify({"error": "Tag is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Find notes with the given tag
        note_ids = col.find_notes(f"tag:{tag}")
        card_ids = []
        for note_id in note_ids:
            card_ids.extend(col.card_ids_of_note(note_id))

        if not card_ids:
            col.close()
            return jsonify({"error": "No cards found with the given tag"}), 404

        col.remove_notes_by_card(card_ids)
        col.close()
        return jsonify({"message": f"Cards with tag '{tag}' deleted successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@cards.route('/api/cards/delete/by-deck', methods=['DELETE'])
def delete_cards_by_deck():
    data = request.json
    deck_identifier = data.get('deck')
    username = data.get('username')

    if not deck_identifier:
        return jsonify({"error": "Deck identifier (name or ID) is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Try to interpret the deck identifier as an ID
        try:
            deck_id = int(deck_identifier)
        except ValueError:
            # If conversion fails, treat it as a deck name
            deck_id = col.decks.id_for_name(deck_identifier)
            if not deck_id:
                return jsonify({"error": "Deck not found"}), 404

        # Get all card IDs for the specified deck
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        if not card_ids:
            return jsonify({"error": "No cards found in the specified deck"}), 404

        # Remove notes by card IDs
        col.remove_notes_by_card(card_ids)
        col.close()
        return jsonify({"message": f"Cards from deck '{deck_identifier}' deleted successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-ease', methods=['GET'])
def get_cards_by_ease():
    """
    Find difficult cards based on predefined criteria:
    - High number of reviews relative to interval
    - Low ease factor
    - Minimum number of reviews
    """
    data = request.json
    username = data.get('username')
    deck_id = data.get('deck_id')
    inclusions = data.get('inclusions', None)
    
    # Parameters for defining difficult cards
    min_reviews = data.get('min_reviews', 3)  # Minimum number of reviews to consider
    min_factor = data.get('min_factor', 2000)  # Minimum ease factor (stored as permille, 2500 = 250%)
    max_factor = data.get('max_factor', 2750)  # Maximum ease factor (stored as permille, 2500 = 250%)
    min_ratio = data.get('min_ratio', 0.2)  # Minimum reviews/interval ratio
    max_ratio = data.get('max_ratio', 1.0)  # Maximum reviews/interval ratio
    include_suspended = data.get('include_suspended', False)  # Whether to include suspended cards
    include_fields = data.get('include_fields', True)  # Whether to include field contents
    
    if not deck_id or not username:
        return jsonify({"error": "deck_id and username are required"}), 400
    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    
    try:
        deck_id = int(deck_id)
        # Get all cards in the deck
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        difficult_cards = []
        
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            
            # Skip suspended cards if not including them
            if not include_suspended and card.queue == QUEUE_TYPE_SUSPENDED:
                continue
                
            # Skip new cards (no review history)
            if card.queue == QUEUE_TYPE_NEW:
                continue
                
            # Get card stats - using the correct property names from Anki's codebase
            reviews = card.reps  # Number of reviews
            interval = card.ivl  # Current interval
            factor = card.factor  # Ease factor (stored as permille, 2500 = 250%)
            
            # Calculate ratio of reviews to interval
            ratio = reviews / interval if interval > 0 else float('inf')
            
            # Check if this card meets the difficult criteria
            if (reviews >= min_reviews and 
                factor >= min_factor and 
                factor <= max_factor and 
                ratio >= min_ratio and
                ratio <= max_ratio):
                
                note = col.get_note(card.nid)
                card_data = {
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "queue": card.queue,
                    "ease_factor": factor / 10,  # Convert to percentage (250 = 250%)
                    "interval": interval,
                    "reviews": reviews,
                    "lapses": card.lapses,
                    "review_to_interval_ratio": ratio,
                    "tags": note.tags
                }
                
                # Include field contents if requested
                if include_fields:
                    if inclusions is not None:
                        field_contents = {field: note[field] for field in inclusions if field in note.keys()}
                    else:
                        field_contents = {field_name: note[field_name] for field_name in note.keys()}
                    card_data["fields"] = field_contents
                
                difficult_cards.append(card_data)
        
        col.close()
        return jsonify(difficult_cards), 200
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-learning-metrics', methods=['GET'])
def get_cards_by_learning_metrics():
    """
    Flexible filtering of cards based on various learning metrics:
    - Reviews count
    - Interval length
    - Ease factor
    - Review-to-interval ratio
    - Lapses
    """
    data = request.json
    username = data.get('username')
    deck_id = data.get('deck_id')
    inclusions = data.get('inclusions', None)
    
    # Filter parameters
    min_reviews = data.get('min_reviews')
    max_reviews = data.get('max_reviews')
    min_interval = data.get('min_interval')
    max_interval = data.get('max_interval')
    min_factor = data.get('min_factor')
    max_factor = data.get('max_factor')
    min_lapses = data.get('min_lapses')
    max_lapses = data.get('max_lapses')
    min_ratio = data.get('min_ratio')
    max_ratio = data.get('max_ratio')
    include_suspended = data.get('include_suspended', False)
    include_new = data.get('include_new', False)
    include_fields = data.get('include_fields', True)
    limit = data.get('limit', 100)  # Default limit to prevent excessively large responses
    
    if not deck_id or not username:
        return jsonify({"error": "deck_id and username are required"}), 400
    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    
    try:
        deck_id = int(deck_id)
        # Get all cards in the deck
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        filtered_cards = []
        
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            
            # Skip suspended cards if not including them
            if not include_suspended and card.queue == QUEUE_TYPE_SUSPENDED:
                continue
                
            # Skip new cards if not including them
            if not include_new and card.queue == QUEUE_TYPE_NEW:
                continue
                
            # Get card stats - using the correct property names from Anki's codebase
            reviews = card.reps
            interval = card.ivl
            factor = card.factor / 10  # Convert to percentage (250 = 250%)
            lapses = card.lapses
            
            # Calculate ratio of reviews to interval
            ratio = reviews / interval if interval > 0 else float('inf')
            
            # Apply filters
            if ((min_reviews is not None and reviews < min_reviews) or
                (max_reviews is not None and reviews > max_reviews) or
                (min_interval is not None and interval < min_interval) or
                (max_interval is not None and interval > max_interval) or
                (min_factor is not None and factor < min_factor) or
                (max_factor is not None and factor > max_factor) or
                (min_lapses is not None and lapses < min_lapses) or
                (max_lapses is not None and lapses > max_lapses) or
                (min_ratio is not None and ratio < min_ratio) or
                (max_ratio is not None and ratio > max_ratio)):
                continue
            
            note = col.get_note(card.nid)
            card_data = {
                "id": card.id,
                "note_id": card.nid,
                "deck_id": card.did,
                "queue": card.queue,
                "ease_factor": factor,
                "interval": interval,
                "reviews": reviews,
                "lapses": lapses,
                "review_to_interval_ratio": ratio,
                "tags": note.tags
            }
            
            # Include field contents if requested
            if include_fields:
                if inclusions is not None:
                    field_contents = {field: note[field] for field in inclusions if field in note.keys()}
                else:
                    field_contents = {field_name: note[field_name] for field_name in note.keys()}
                card_data["fields"] = field_contents
            
            filtered_cards.append(card_data)
            
            # Apply limit
            if len(filtered_cards) >= limit:
                break
        
        col.close()
        return jsonify(filtered_cards), 200
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/reset-difficult', methods=['POST'])
def reset_difficult_cards():
    """
    Find and reset cards that meet the difficult criteria.
    This can help break the 'ease hell' cycle by giving problematic cards a fresh start.
    """
    data = request.json
    username = data.get('username')
    deck_id = data.get('deck_id')
    
    # Parameters for defining difficult cards to reset
    min_reviews = data.get('min_reviews', 5)
    max_factor = data.get('max_factor', 1800)  # Lower threshold than just viewing
    min_ratio = data.get('min_ratio', 0.3)     # Higher threshold than just viewing
    min_lapses = data.get('min_lapses', 3)     # Cards that have lapsed multiple times
    
    if not deck_id or not username:
        return jsonify({"error": "deck_id and username are required"}), 400
    
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    
    try:
        deck_id = int(deck_id)
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        cards_to_reset = []
        
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            
            # Skip new cards
            if card.queue == QUEUE_TYPE_NEW:
                continue
                
            reviews = card.reps
            interval = card.ivl
            factor = card.factor
            lapses = card.lapses
            
            ratio = reviews / interval if interval > 0 else float('inf')
            
            if (reviews >= min_reviews and 
                factor <= max_factor and 
                ratio >= min_ratio and
                lapses >= min_lapses):
                cards_to_reset.append(card_id)
        
        if cards_to_reset:
            col.sched.schedule_cards_as_new(cards_to_reset)
            col.close()
            return jsonify({
                "message": f"Reset {len(cards_to_reset)} difficult cards",
                "cards_reset": len(cards_to_reset)
            }), 200
        else:
            col.close()
            return jsonify({"message": "No difficult cards found that meet the criteria"}), 200
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-note-id/<note_id>', methods=['GET'])
def get_cards_by_note_id(note_id):
    data = request.json or {}
    username = data.get('username')
    inclusions = data.get('inclusions', None)

    if not username:
        return jsonify({"error": "Username is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        note_id = int(note_id)
        col = Collection(collection_path)
        # First check if the note exists
        try:
            note = col.get_note(note_id)
        except Exception:
            col.close()
            return jsonify({"error": f"Note with ID {note_id} not found"}), 404
            
        card_ids = col.card_ids_of_note(note_id)
        
        if not card_ids:
            col.close()
            return jsonify({"error": f"No cards found for note ID {note_id}"}), 404
            
        cards = []
        for card_id in card_ids:
            card = col.get_card(card_id)
            if inclusions is not None:
                field_contents = {field: note[field] for field in inclusions if field in note.keys()}
            else:
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
            cards.append({
                "id": card.id,
                "note_id": card.nid,
                "deck_id": card.did,
                "fields": field_contents,
                "queue": card.queue,
                "tags": note.tags,
                "due": getattr(card, 'due', None)
            })
        col.close()
        return jsonify(cards), 200
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid note ID format"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-field-content', methods=['GET'])
def get_cards_by_field_content():
    data = request.json
    username = data.get('username')
    field_name = data.get('field_name')
    field_content = data.get('field_content')
    exact_match = data.get('exact_match', True)
    deck_id = data.get('deck_id')
    inclusions = data.get('inclusions', None)

    if not username or not field_name or not field_content:
        return jsonify({"error": "username, field_name, and field_content are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Construct the search query based on exact_match parameter
        if exact_match:
            # For exact match, we use the "field:content" syntax
            search_query = f"\"{field_name}:{field_content}\""
        else:
            # For partial match, we use the "field:*content*" syntax
            search_query = f"\"{field_name}:*{field_content}*\""
        
        # Add deck restriction if deck_id is provided
        if deck_id:
            deck_id = int(deck_id)
            search_query = f"deck:{deck_id} {search_query}"
        
        # Find notes matching the search query
        note_ids = col.find_notes(search_query)
        
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            note = col.get_note(note_id)
            
            # Filter fields based on inclusions if provided
            if inclusions is not None:
                field_contents = {field: note[field] for field in inclusions if field in note.keys()}
            else:
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
            
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "fields": field_contents,
                    "queue": card.queue,
                    "tags": note.tags
                })
        
        col.close()
        return jsonify(cards), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@cards.route('/api/cards/by-field-substring', methods=['GET'])
def get_cards_by_field_substring():
    data = request.json
    username = data.get('username')
    field_name = data.get('field_name')
    substring = data.get('substring')
    case_sensitive = data.get('case_sensitive', False)
    deck_id = data.get('deck_id')
    inclusions = data.get('inclusions', None)

    if not username or not field_name or not substring:
        return jsonify({"error": "username, field_name, and substring are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Construct the search query based on case sensitivity
        # Note: Anki's regex search is case-insensitive by default
        search_modifier = "re" if case_sensitive else "re:i"
        # The regex pattern will search for the substring within the field contents
        search_query = f"{search_modifier}:{field_name}:.*{substring}.*"
        
        # Add deck restriction if deck_id is provided
        if deck_id:
            deck_id = int(deck_id)
            search_query = f"deck:{deck_id} {search_query}"
        
        # Find notes matching the search query
        note_ids = col.find_notes(search_query)
        
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            note = col.get_note(note_id)
            
            # Filter fields based on inclusions if provided
            if inclusions is not None:
                field_contents = {field: note[field] for field in inclusions if field in note.keys()}
            else:
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
            
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "fields": field_contents,
                    "queue": card.queue,
                    "tags": note.tags
                })
        
        col.close()
        return jsonify(cards), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e), "query": search_query}), 500

@cards.route('/api/cards/advanced-field-search', methods=['POST'])
def advanced_field_search():
    data = request.json
    username = data.get('username')
    field_conditions = data.get('field_conditions', [])
    join_operator = data.get('join_operator', 'AND')  # 'AND' or 'OR'
    deck_id = data.get('deck_id')
    inclusions = data.get('inclusions', None)

    if not username or not field_conditions:
        return jsonify({"error": "username and field_conditions are required"}), 400

    if join_operator not in ('AND', 'OR'):
        return jsonify({"error": "join_operator must be 'AND' or 'OR'"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        # Build the search query from field conditions
        condition_queries = []
        
        for condition in field_conditions:
            field_name = condition.get('field_name')
            operation = condition.get('operation', 'is')  # 'is', 'contains', 'regex'
            value = condition.get('value')
            case_sensitive = condition.get('case_sensitive', False)
            
            if not field_name or not value:
                continue
                
            if operation == 'is':
                condition_queries.append(f"\"{field_name}:{value}\"")
            elif operation == 'contains':
                condition_queries.append(f"\"{field_name}:*{value}*\"")
            elif operation == 'regex':
                re_modifier = "re" if case_sensitive else "re:i"
                condition_queries.append(f"{re_modifier}:{field_name}:{value}")
        
        # Join the conditions with the specified operator
        search_query = f" {join_operator} ".join(condition_queries)
        
        # Add deck restriction if deck_id is provided
        if deck_id:
            deck_id = int(deck_id)
            search_query = f"deck:{deck_id} {search_query}"
        
        # Find notes matching the search query
        note_ids = col.find_notes(search_query)
        
        cards = []
        for note_id in note_ids:
            card_ids = col.card_ids_of_note(note_id)
            note = col.get_note(note_id)
            
            # Get field contents
            if inclusions is not None:
                field_contents = {field: note[field] for field in inclusions if field in note.keys()}
            else:
                field_contents = {field_name: note[field_name] for field_name in note.keys()}
            
            for card_id in card_ids:
                card = col.get_card(CardId(card_id))
                cards.append({
                    "id": card.id,
                    "note_id": card.nid,
                    "deck_id": card.did,
                    "fields": field_contents,
                    "queue": card.queue,
                    "tags": note.tags
                })
        
        col.close()
        return jsonify({"cards": cards, "query": search_query, "count": len(cards)}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e), "query": search_query}), 500
