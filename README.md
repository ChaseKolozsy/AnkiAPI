# AnkiAPI

AnkiAPI is a lightweight REST API that wraps the Anki spaced repetition engine for use in external applications — no Anki GUI required. It uses Flask to serve the API and the native `anki` Python package to interact with Anki's database directly.

## AnkiClient

[Visit AnkiClient for premade Python functions for calling the API](https://github.com/ChaseKolozsy/AnkiClient)

## Features

- Daily study materials generated based on Anki's spaced repetition schedule.
- Full card, deck, note type, and study session management via REST endpoints.
- AnkiWeb sync support (login, push/pull collections).
- Import/export of `.apkg` packages and CSV files.
- Cross-platform: works on Windows, macOS, and Linux.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/ChaseKolozsy/AnkiAPI.git
    cd AnkiAPI
    ```

2. Create a virtual environment and install dependencies:

    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate

    pip install anki flask
    ```

3. Start the server:

    ```bash
    python anki_api_server.py
    ```

    The API will be available at `http://localhost:5001`.

## Directory Structure

- `anki_api_server.py`: Flask app entry point — registers all blueprints and starts the server on port 5001.
- `anki_paths.py`: Cross-platform Anki collection path locator (Windows/macOS/Linux).
- `blueprint_cards.py`: Card CRUD, search, suspend, bury, reschedule, reposition.
- `blueprint_decks.py`: Deck CRUD, configuration, card listing.
- `blueprint_notetypes.py`: Note type management (create, modify fields, set sort field).
- `blueprint_study_sessions.py`: Study session management (start, flip, answer, close, custom sessions).
- `blueprint_users.py`: Anki profile management and AnkiWeb sync login.
- `blueprint_db.py`: Database sync operations (push/pull with AnkiWeb).
- `blueprint_imports.py`: Import `.apkg` packages, CSV files, and media.
- `blueprint_exports.py`: Export collections and notes.
- `qt/`: Build tooling for Qt compatibility across platforms.

## Usage

1. Start the server: `python anki_api_server.py`
2. Use the API endpoints directly or through [AnkiClient](https://github.com/ChaseKolozsy/AnkiClient).

Quick test:

```bash
curl -X POST "http://localhost:5001/api/users/create/User%201"
```

## Anki Collection Paths

The server reads Anki data from the standard locations:

- **Windows:** `%APPDATA%\Anki2\{username}`
- **macOS:** `~/Library/Application Support/Anki2/{username}`
- **Linux:** `~/.local/share/Anki2/{username}`

## Contributing

Contributions welcome! Fork the repository and submit pull requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Anki](https://github.com/ankitects/anki): The powerful, intelligent flashcard software that this project integrates with.
