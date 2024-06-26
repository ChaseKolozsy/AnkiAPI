# AnkiApi

AnkiApi is a project designed to enable the incorporation of the Anki database and spaced repetition system into applications that can benefit from spaced repetition without the Anki GUI. It is meant to be fully featured as far as possible to the exclusion of the GUI. It uses Flask to serve the API and Docker to containerize the application.

## AnkiClient

[Visit AnkiClient for premade python functions for calling the API that can be used in conjunction with this project](https://github.com/ChaseKolozsy/AnkiClient)

## Features

- Daily study materials generated based on Anki's spaced repetition schedule.
- Integration with Anki notes for seamless conversation and review.
- API endpoints for various functionalities including decks, cards, users, imports, exports, and note types.

## Installation

To set up the AnkiApi project, follow these steps:

1. Clone the AnkiApi repository:

    ```bash
    git clone https://github.com/ChaseKolozsy/AnkiAPI.git
    cd AnkiApi
    ```

2. Clone the Anki repository inside the `AnkiApi` directory:

    ```bash
    git clone https://github.com/ankitects/anki.git
    ```

3. Navigate to the `AnkiAPI/docker` directory  and run the `build.sh` script: 

    ```bash
    cd docker
    ./build.sh
    ```

    - > There is another dockerfile inside of the `anki/docs/docker` directory, but it is not recommended to use this one because it will not work without modifying it like the one in this project.

## Directory Structure

- `docker/`: Contains Docker-related files.
- `qt/`: This is necessary for making the docker build compatible with macos, linux, and windows. It will not compile the qt framework if qt is not compatible with the architecture. 
- `anki/`: Cloned Anki repository.
- `anki_api_server.py`: This is the entrypoint to the Anki API and the docker container. It is the main server script to run the Anki API.
- `blueprint_decks.py`: Blueprint for decks-related API endpoints.
- `blueprint_db.py`: Blueprint for database-related API endpoints.
- `blueprint_imports.py`: Blueprint for imports-related API endpoints.
- `blueprint_users.py`: Blueprint for users-related API endpoints.
- `blueprint_cards.py`: Blueprint for cards-related API endpoints.
- `blueprint_exports.py`: Blueprint for exports-related API endpoints.
- `blueprint_notetypes.py`: Blueprint for note types-related API endpoints.
- `blueprint_study_sessions.py`: Blueprint for study sessions-related API endpoints.

## Usage

1. Start the Anki API server by running the `build.sh` script, or by choosing which command from the script you would like to run in isolation without running the build.sh script. 
2. Once the docker container is created, you can run it independently of this repository and it can be interacted with through the AnkiClient. You can also create your own functions to interact with the endpoints in your applications based on the provided API endpoints. Eventually an OpenApi spec will be provided to document the API endpoints.
3. Use the provided API endpoints to interact with your Anki database for various functionalities.
4. To rebuild the docker container, run the `rebuild.sh` script, wait for it to load the docker container in interactive mode, then, open a new terminal and run the `restore.sh` script. This will delete all Docker containers and images that have anki-api in their name. It also deletes dangling images and caches so comment that out if you don't want to delete those. This will preserve the collection from the destroyed container and restore it when the new container is created. This is done automatically in a 2 step process, `rebuild.sh` and `restore.sh`.

## Contributing

We welcome contributions to improve AnkiApi! Please fork the repository and submit pull requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Anki](https://github.com/ankitects/anki): The powerful, intelligent flashcard software that this project integrates with.