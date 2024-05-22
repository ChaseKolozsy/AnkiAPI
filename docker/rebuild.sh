#!/bin/bash

# Delete all containers
docker container rm $(docker container ls -aq)

# Delete all images
docker image rm $(docker image ls -aq)

# Delete all builds
echo y | docker system prune --all --volumes

cp ../anki_api_server.py ../anki/
cp ../blueprint_decks.py ../anki/
cp ../blueprint_exports.py ../anki/
cp ../blueprint_imports.py ../anki/
cp ../blueprint_notetypes.py ../anki/
cp ../blueprint_users.py ../anki/
cp ../blueprint_cards.py ../anki/

cp ../qt/tools/new/build_ui.py ../anki/qt/tools/
# Rebuild the Docker image
docker build --no-cache --tag anki-api --file Dockerfile ../anki/

rm ../anki/anki_api_server.py
rm ../anki/blueprint_decks.py
rm ../anki/blueprint_exports.py
rm ../anki/blueprint_imports.py
rm ../anki/blueprint_notetypes.py
rm ../anki/blueprint_users.py
rm ../anki/blueprint_cards.py
cp ../qt/tools/old/build_ui.py ../anki/qt/tools/

# Run the Docker container
docker run -p 5001:5001 --name anki-api anki-api

# Delete the copied files


