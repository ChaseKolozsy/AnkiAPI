#!/bin/bash

API_URL="http://localhost:5001/api"
USERNAME="User 1"

# Step 1: Copy necessary files to the build context
cp ../anki_api_server.py ../anki/
cp ../blueprint_decks.py ../anki/
cp ../blueprint_exports.py ../anki/
cp ../blueprint_imports.py ../anki/
cp ../blueprint_notetypes.py ../anki/
cp ../blueprint_users.py ../anki/
cp ../blueprint_cards.py ../anki/
cp ../blueprint_study_sessions.py ../anki/
cp ../blueprint_db.py ../anki/
cp ../qt/tools/new/build_ui.py ../anki/qt/tools/

# Step 2: Rebuild the Docker image
docker build --no-cache --tag anki-api --file Dockerfile ../anki/

# Step 3: Clean up copied files
rm ../anki/anki_api_server.py
rm ../anki/blueprint_decks.py
rm ../anki/blueprint_exports.py
rm ../anki/blueprint_imports.py
rm ../anki/blueprint_notetypes.py
rm ../anki/blueprint_users.py
rm ../anki/blueprint_cards.py
rm ../anki/blueprint_study_sessions.py
rm ../anki/blueprint_db.py
cp ../qt/tools/old/build_ui.py ../anki/qt/tools/

# Step 4: Run the Docker container
docker run -p 5001:5001 --cpus=1 --name anki-api anki-api

