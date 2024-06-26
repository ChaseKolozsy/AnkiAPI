# blueprint_decks.py
from flask import jsonify, request, Blueprint
from anki.collection import Collection

from anki import deck_config_pb2, decks_pb2
from google.protobuf.descriptor import EnumDescriptor
DeckConfig = deck_config_pb2.DeckConfig

from anki.models import NotetypeId

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

from blueprint_cards import change_notetype


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

decks = Blueprint('decks', __name__)

###------------------------- HELPERS -------------------------###
def create_deck_config(*, 
                       col: Collection, 
                       name: str, 
                       new_cards_per_day: int, 
                       review_cards_per_day: int, 
                       new_mix: int, 
                       interday_learning_mix: int, 
                       review_order: int) -> int:
    """
    Create a new deck configuration with specified limits for new and review cards,
    and settings for new card mix, interday learning mix, and review order.
    """
    # Create a new configuration
    new_config = col.decks.add_config(name)

    # Set new cards per day
    new_config['new']['perDay'] = new_cards_per_day

    # Set review cards per day
    new_config['rev']['perDay'] = review_cards_per_day

    # Set new card mix
    new_config['new_mix'] = new_mix

    # Set interday learning mix
    new_config['interday_learning_mix'] = interday_learning_mix

    # Set review order
    new_config['review_order'] = review_order

    # Save the configuration
    col.decks.update_config(new_config)

    return new_config['id']

def apply_config_to_deck(col, deck_id, config_id):
    """
    Apply a specific configuration to a deck.
    """
    deck = col.decks.get(DeckId(deck_id), default=True)
    if not deck:
        raise ValueError("Deck not found")

    # Set the configuration ID for the deck
    deck['conf'] = config_id

    # Save the deck
    col.decks.save(deck)

def update_deck_review_mix(*, 
                           col: Collection, 
                           deck_id: int, 
                           new_mix: int, 
                           interday_learning_mix: int, 
                           review_order: int): 
    """
    Update the mix settings for new cards, learning cards, and review order in a deck configuration.
    """
    # Fetch the current configuration for the deck
    deck_conf = col.decks.config_dict_for_deck_id(DeckId(deck_id))

    # Update the mix settings
    deck_conf['new_mix'] = new_mix
    deck_conf['interday_learning_mix'] = interday_learning_mix
    deck_conf['review_order'] = review_order

    # Save the updated configuration
    col.decks.update_config(deck_conf)

def enum_to_dict(enum: EnumDescriptor):
    """Converts a protobuf EnumDescriptor to a dictionary."""
    return {name: value.number for name, value in enum.values_by_name.items()}

###------------------------- DECKS -------------------------###
@decks.route('/api/decks/create/<deck_name>', methods=['POST'])
def create_deck(deck_name):
    data = request.json
    username = data.get('username')
    if not deck_name:
        return jsonify({"error": "Deck name is required"}), 400
    if not username:
        return jsonify({"error": "Username is required"}), 400
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    result = col.decks.add_normal_deck_with_name(deck_name)
    col.close()
    return jsonify({"id": result.id, "name": deck_name}), 201

@decks.route('/api/decks/<deck_id>/change-notetype', methods=['POST'])
def change_deck_notetype(deck_id):
    data = request.json
    new_notetype_id = data.get('new_notetype_id')
    match_by_name = data.get('match_by_name', True)  # Optional, defaults to True
    username = data.get('username')

    if not new_notetype_id:
        return jsonify({"error": "New notetype ID is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        new_notetype_id = int(new_notetype_id)
        card_ids = col.decks.cids(DeckId(deck_id))
        for card_id in card_ids:
            note_id = col.get_card(CardId(card_id)).nid
            change_notetype(col, note_id, new_notetype_id, match_by_name)
        col.close()
        return jsonify({"message": "Notetypes changed successfully"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/<deck_id>/set-new-card-limit', methods=['POST'])
def set_new_card_limit(deck_id):
    data = request.json
    new_card_limit = data.get('new_card_limit')
    username = data.get('username')

    if new_card_limit is None:
        return jsonify({"error": "new_card_limit is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        new_card_limit = int(new_card_limit)

        # Get the deck configuration dictionary
        deck_conf = col.decks.config_dict_for_deck_id(DeckId(deck_id))

        # Set the new card limit
        deck_conf['new']['perDay'] = new_card_limit

        # Save the updated configuration back to the collection
        col.decks.update_config(deck_conf)
        col.close()

        return jsonify({"message": f"New card limit for deck {deck_id} set to {new_card_limit}"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid deck ID or new card limit"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500
    
@decks.route('/api/decks/set-current/<deck_id>', methods=['POST'])
def set_current_deck(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        deck_id = int(deck_id)
        result = col.decks.set_current(DeckId(deck_id))
        col.close()
        return jsonify({"message": f"Current deck set to {deck_id}"}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500



@decks.route('/api/decks/config/create', methods=['POST'])
def create_config():
    data = request.json
    name = data.get('name')
    new_cards_per_day = data.get('new_cards_per_day')
    review_cards_per_day = data.get('review_cards_per_day')
    new_mix = data.get('new_mix')
    interday_learning_mix = data.get('interday_learning_mix')
    review_order = data.get('review_order')
    username = data.get('username')

    if not name or new_cards_per_day is None or review_cards_per_day is None or new_mix is None or interday_learning_mix is None or review_order is None or username is None:
        return jsonify({"error": "name, new_cards_per_day, review_cards_per_day, new_mix, interday_learning_mix, and review_order are required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        config_id = create_deck_config(col=col, 
                                       name=name, 
                                       new_cards_per_day=new_cards_per_day, 
                                       review_cards_per_day=review_cards_per_day, 
                                       new_mix=new_mix, 
                                       interday_learning_mix=interday_learning_mix, 
                                       review_order=review_order
                                       )
        col.close()
        return jsonify({"message": "Configuration created successfully", "config_id": config_id}), 201
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/<deck_id>/config/apply', methods=['POST'])
def apply_config(deck_id):
    data = request.json
    config_id = data.get('config_id')
    username = data.get('username')

    if config_id is None:
        return jsonify({"error": "config_id is required"}), 400

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        deck_id = int(deck_id)
        config_id = int(config_id)
        apply_config_to_deck(col, deck_id, config_id)
        col.close()
        return jsonify({"message": f"Configuration {config_id} applied to deck {deck_id} successfully"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid deck ID or config ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/<deck_id>/update_mix', methods=['POST'])
def update_deck_mix(deck_id):
    data = request.json
    new_mix = data.get('new_mix')
    interday_learning_mix = data.get('interday_learning_mix')
    review_order = data.get('review_order')
    username = data.get('username')

    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)

    try:
        update_deck_review_mix(col=col, 
                               deck_id=deck_id, 
                               new_mix=new_mix, 
                               interday_learning_mix=interday_learning_mix, 
                               review_order=review_order)
        return jsonify({"message": "Deck mix settings updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

@decks.route('/api/decks/delete/<deck_id>', methods=['DELETE'])
def delete_deck(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        deck_id = int(deck_id)
        col = Collection(collection_path)
        col.decks.remove([DeckId(deck_id)])
        col.close()
        return jsonify({"message": f"Deck {deck_id} deleted successfully"}), 200
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/delete-filtered/<deck_id>', methods=['DELETE'])
def delete_filtered_deck(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        deck_id = int(deck_id)
        col = Collection(collection_path)

        # Get the filtered deck
        filtered_deck = col.decks.get(deck_id)
        if not filtered_deck or not filtered_deck['dyn']:
            col.close()
            return jsonify({"error": "Deck is not a filtered deck"}), 400

        # Get all card IDs in the filtered deck
        card_ids = col.decks.cids(DeckId(deck_id), children=False)

        # Move the cards back to their original decks
        for card_id in card_ids:
            card = col.get_card(CardId(card_id))
            col.set_deck([card_id], card.odid)

        # Delete the filtered deck
        col.decks.remove([DeckId(deck_id)])
        col.close()

        return jsonify({"message": f"Filtered deck {deck_id} emptied and deleted successfully"}), 200

    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/rename/<deck_id>/<new_name>', methods=['PUT'])
def rename_deck(deck_id, new_name):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    
    try:
        deck_id = int(deck_id)
        result = col.decks.rename(deck_id, new_name)
        col.close()
        return jsonify({"message": f"Deck {deck_id} renamed to {new_name}"}), 200
    except ValueError:
        col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks', methods=['GET'])
def get_decks():
    username = request.json.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    decks = col.decks.all_names_and_ids()
    col.close()
    decks_list = [{"id": deck.id, "name": deck.name} for deck in decks]
    return jsonify(decks_list)

@decks.route('/api/decks/<deck_id>', methods=['GET'])
def get_deck(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None
    
    try:
        deck_id = int(deck_id)
        col = Collection(collection_path)
        deck = col.decks.get(deck_id)
        col.close()
        return jsonify({"id": deck['id'], "name": deck['name']})
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/<deck_id>/cards', methods=['GET'])
def get_cards_in_deck(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        deck_id = int(deck_id)
        col = Collection(collection_path)
        # Assuming `cids` is the correct method to get card IDs from a deck
        card_ids = col.decks.cids(DeckId(deck_id), children=True)
        cards = [col.get_card(CardId(card_id)) for card_id in card_ids]  # Use get_card instead of col.cards.get
        card_details = [{'id': card.id, 'note_id': card.nid, 'deck_id': card.did} for card in cards]
        col.close()
        return jsonify(card_details)
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/get-current-id', methods=['GET'])
def get_current_deck_id():
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        current_deck_id = col.decks.get_current_id()
        col.close()
        return jsonify({"current_deck_id": current_deck_id}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/current', methods=['GET'])
def get_current_deck():
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        current_deck = col.decks.current()
        col.close()
        return jsonify({"current_deck": current_deck}), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500

@decks.route('/api/decks/active', methods=['GET'])
def get_active_decks():
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = Collection(collection_path)
    try:
        active_decks = col.decks.active()
        active_decks_info = [{"deck_id": deck_id} for deck_id in active_decks]
        col.close()
        return jsonify(active_decks_info), 200
    except Exception as e:
        col.close()
        return jsonify({"error": str(e)}), 500


@decks.route('/api/decks/config/enums', methods=['GET'])
def get_deck_config_enums():
    # Access the Config inner class
    config_class = DeckConfig.Config

    # Dynamically build the dictionary of enums
    enums_dict = {
        "NewCardInsertOrder": enum_to_dict(config_class.NewCardInsertOrder.DESCRIPTOR),
        "NewCardGatherPriority": enum_to_dict(config_class.NewCardGatherPriority.DESCRIPTOR),
        "NewCardSortOrder": enum_to_dict(config_class.NewCardSortOrder.DESCRIPTOR),
        "ReviewCardOrder": enum_to_dict(config_class.ReviewCardOrder.DESCRIPTOR),
        "ReviewMix": enum_to_dict(config_class.ReviewMix.DESCRIPTOR),
        "LeechAction": enum_to_dict(config_class.LeechAction.DESCRIPTOR),
        "AnswerAction": enum_to_dict(config_class.AnswerAction.DESCRIPTOR),
        "QuestionAction": enum_to_dict(config_class.QuestionAction.DESCRIPTOR)
    }

    return jsonify(enums_dict), 200

@decks.route('/api/decks/<deck_id>/config', methods=['GET'])
def get_deck_config(deck_id):
    data = request.json
    username = data.get('username')
    collection_path = os.path.expanduser(f"~/.local/share/Anki2/{username}/collection.anki2")
    col = None

    try:
        deck_id = int(deck_id)  # Ensure deck_id is an integer
        col = Collection(collection_path)
        deck_config = col.decks.config_dict_for_deck_id(DeckId(deck_id))
        
        if deck_config is None:
            col.close()
            return jsonify({"error": "Deck configuration not found"}), 404
        
        col.close()
        return jsonify({"config": deck_config}), 200
    except ValueError:
        if col:
            col.close()
        return jsonify({"error": "Invalid deck ID"}), 400
    except Exception as e:
        if col:
            col.close()
        return jsonify({"error": str(e)}), 500


