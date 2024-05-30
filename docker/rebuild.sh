#!/bin/bash

API_URL="http://localhost:5001/api"
EXPORT_PATH="/tmp/anki_collection.apkg"
ANKI_USERNAME="User 1"

# Step 1: Export the collection
curl -X POST "${API_URL}/export-collection-package?username=$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')" \
     -H "Content-Type: application/json" \
     -d "{\"out_path\": \"/tmp/anki_collection.apkg\", \"include_media\": true, \"legacy\": true}" \
     --fail --silent --show-error -o ${EXPORT_PATH}

# Check if the export was successful
if [ $? -ne 0 ]; then
    echo "Failed to export collection. Aborting rebuild."
    #exit 1
fi

# Step 2: Stop and remove the specific container
docker container stop anki-api
docker container rm anki-api

# Step 3: Remove specific images related to anki-api
docker image rm anki-api

# Step 5: Prune unused networks, dangling images, and build cache
docker system prune --force --volumes

# Step 6: Copy necessary files to the build context
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

# Step 7: Rebuild the Docker image
docker build --no-cache --tag anki-api --file Dockerfile ../anki/

# Step 8: Clean up copied files
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

# Step 9: Run the Docker container
docker run -p 5001:5001 --name anki-api anki-api

