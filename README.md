# AnkiApi

AnkiApi is a project designed to enable the incorporation of theAnki database and spaced repetition system into applications that can benefit from spaced repetition without the Anki GUI. It is meant to be fully featured as far as possible to the exclusion of the GUI.

## Features

- Daily study materials generated based on Anki's spaced repetition schedule.
- Integration with Anki notes for seamless conversation and review.
- API endpoints for various functionalities including decks, cards, users, imports, exports, and note types.

## Installation

To set up the AnkiApi project, follow these steps:

1. Clone the AnkiApi repository:

    ```bash
    git clone <your-repo-url>
    cd AnkiApi
    ```

2. Clone the Anki repository inside the `AnkiApi` directory:

    ```bash
    git clone https://github.com/ankitects/anki.git
    ```

3. Navigate to the `docker` directory and run the `rebuild.sh` script:

    ```bash
    cd docker
    ./rebuild.sh
    ```

    > **WARNING:** Running `rebuild.sh` will delete all Docker containers, images, and volumes. This script will be modified in the future to avoid this.

## Directory Structure

- `docker/`: Contains Docker-related files.
- `qt/`: This is necessary for making the docker build compatible with macos, linux, and windows. It will not compile the qt framework if qt is not compatible with the architecture. 
- `anki/`: Cloned Anki repository.
- `anki_api_server.py`: Main server script to run the Anki API.
- `blueprint_decks.py`: Blueprint for decks-related API endpoints.
- `blueprint_db.py`: Blueprint for database-related API endpoints.
- `blueprint_imports.py`: Blueprint for imports-related API endpoints.
- `blueprint_users.py`: Blueprint for users-related API endpoints.
- `blueprint_cards.py`: Blueprint for cards-related API endpoints.
- `blueprint_exports.py`: Blueprint for exports-related API endpoints.
- `blueprint_notetypes.py`: Blueprint for note types-related API endpoints.

## Usage

1. Start the Anki API server by running the `anki_api_server.py` script.
2. Use the provided API endpoints to interact with your Anki database for various functionalities.

## Contributing

We welcome contributions to improve AnkiApi! Please fork the repository and submit pull requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Anki](https://github.com/ankitects/anki): The powerful, intelligent flashcard software that this project integrates with.