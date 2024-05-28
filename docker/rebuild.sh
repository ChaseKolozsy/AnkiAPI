#!/bin/bash

API_URL="http://localhost:5001/api"
EXPORT_PATH="/tmp/anki_collection.apkg"
USERNAME="User 1"

# Step 1: Export the collection
curl -X POST "${API_URL}/export-collection-package?username=${USERNAME}" -H "Content-Type: application/json" -d "{\"out_path\": \"${EXPORT_PATH}\", \"include_media\": true, \"legacy\": true}" --fail --silent --show-error

# Check if the export was successful
if [ $? -ne 0 ]; then
    echo "Failed to export collection. Aborting rebuild."
    exit 1
fi

# Step 2: Stop and remove the specific container
docker container stop anki-api
docker container rm anki-api

# Step 3: Remove specific images related to anki-api
docker image rm anki-api

# Step 4: Prune unused networks, dangling images, and build cache
docker system prune --force --volumes

# Step 5: Copy necessary files to the build context
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

# Step 6: Rebuild the Docker image
docker build --no-cache --tag anki-api --file Dockerfile ../anki/

# Step 7: Clean up copied files
rm ../anki/anki_api_server.py
rm ../anki/blueprint_decks.py
rm ../anki/blueprint_exports.py
rm ../blueprint_imports.py
rm ../anki/blueprint_notetypes.py
rm ../anki/blueprint_users.py
rm ../anki/blueprint_cards.py
rm ../anki/blueprint_study_sessions.py
rm ../anki/blueprint_db.py
cp ../qt/tools/old/build_ui.py ../anki/qt/tools/

# Step 8: Run the Docker container
docker run -d -p 5001:5001 --name anki-api anki-api

# Give the container some time to start
sleep 10

# Step 9: Restore the collection
curl -X POST "${API_URL}/users/create/${USERNAME}"

# Check if the user creation was successful
if [ $? -ne 0 ]; then
    echo "Failed to create user. Aborting restore."
    exit 1
fi

# Step 10: Import the collection
curl -X POST "${API_URL}/import-package?username=${USERNAME}" -F "file=@${EXPORT_PATH}" --fail --silent --show-error

# Check if the import was successful
if [ $? -ne 0 ]; then
    echo "Failed to import collection. Please check the logs for more details."
    exit 1
fi

# Cleanup
rm ${EXPORT_PATH}

echo "Rebuild and collection restore completed successfully."