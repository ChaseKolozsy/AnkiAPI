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
cp ../qt/tools/new/build_ui.py ../anki/qt/tools/

# Step 2: Rebuild the Docker image from source
docker build --no-cache --tag anki-api --file ../Dockerfile.source ../anki/

# Step 3: Clean up copied files
rm ../anki/anki_api_server.py
rm ../anki/blueprint_decks.py
rm ../anki/blueprint_exports.py
rm ../anki/blueprint_imports.py
rm ../anki/blueprint_notetypes.py
rm ../anki/blueprint_users.py
rm ../anki/blueprint_cards.py
rm ../anki/blueprint_study_sessions.py
cp ../qt/tools/old/build_ui.py ../anki/qt/tools/

# Run the Docker container in detached mode
docker run -d -p 5001:5001 --name anki-api --restart unless-stopped anki-api

# Give the container some time to start
sleep 10

# Step 5: Create the user
curl -X POST "${API_URL}/users/create/${USERNAME}"

# Check if the user creation was successful
if [ $? -ne 0 ]; then
    echo "Failed to create user. Please check the logs for more details."
    exit 1
fi

echo "Build and user creation completed successfully."
