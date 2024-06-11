#!/bin/bash

API_URL="http://localhost:5001/api"
EXPORT_PATH="/tmp/anki_collection.apkg"
ANKI_USERNAME="User 1"

# Step 10: Create the user
curl -X POST "${API_URL}/users/create/$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')"

# Check if the user creation was successful
if [ $? -ne 0 ]; then
	echo "Failed to create user. Aborting restore."
	exit 1
fi

# Step 11: Import the collection
curl -X POST "${API_URL}/import-package?username=$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')" \
	-F "file=@${EXPORT_PATH}" \
	--fail --silent --show-error

# Check if the import was successful
if [ $? -ne 0 ]; then
	echo "Failed to import collection. Please check the logs for more details."
	exit 1
fi

# Cleanup
rm ${EXPORT_PATH}

echo "Rebuild and collection restore completed successfully."
