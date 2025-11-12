#!/bin/bash

# --- Configuration ---
REPO_OWNER="ahmedmoselhi"
REPO_NAME="enigma2-plugins-miscellaneous"
FILE_PREFIX="LamedbMerger"
DOWNLOAD_DIR="/var/volatile/tmp"
DEST_DIR="/usr/lib/enigma2/python/Plugins/Extensions"

# GitHub API endpoint to list repository contents
API_URL="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/"

echo "1. Searching for the correct archive name..."

# Use curl and jq to fetch the list of files and filter for the LamedbMerger archive
# The file list is a JSON array. We filter for name starting with "LamedbMerger" and ending with ".tar.gz",
# then take the first result's name.
ARCHIVE_NAME=$(curl -s $API_URL | jq -r ".[] | select(.name | startswith(\"$FILE_PREFIX\") and endswith(\".tar.gz\")) | .name" | head -n 1)

if [ -z "$ARCHIVE_NAME" ]; then
    echo "Error: Could not find any file starting with '$FILE_PREFIX' and ending with '.tar.gz'"
    exit 1
fi

echo "Found file: $ARCHIVE_NAME"
TARGET_FILE="${DOWNLOAD_DIR}/${ARCHIVE_NAME}"
DOWNLOAD_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/master/${ARCHIVE_NAME}"
EXTRACTED_FOLDER="${DOWNLOAD_DIR}/${FILE_PREFIX}" # Still assume extracted folder is just 'LamedbMerger'

# --- 2. Download the Archive ---
echo "Attempting to download $ARCHIVE_NAME..."

# Ensure the download directory exists
mkdir -p "$DOWNLOAD_DIR"

# Download the file
if ! wget -O "$TARGET_FILE" "$DOWNLOAD_URL"; then
    echo "Error: Failed to download the file from $DOWNLOAD_URL"
    exit 1
fi

echo "Download successful to $TARGET_FILE"

# --- 3. Prepare Destination, Extract, and Move ---

# Remove the destination folder if it exists
if [ -d "$DEST_DIR/$FILE_PREFIX" ]; then
    echo "Removing existing destination folder: $DEST_DIR/$FILE_PREFIX"
    rm -rf "$DEST_DIR/$FILE_PREFIX"
fi

# Ensure the parent directory for the destination exists
mkdir -p "$DEST_DIR"

echo "Extracting the archive..."
# Extract the tar.gz file into the download directory
if ! tar -xzf "$TARGET_FILE" -C "$DOWNLOAD_DIR"; then
    echo "Error: Failed to extract the archive $TARGET_FILE"
    exit 1
fi

echo "Moving the extracted folder ($EXTRACTED_FOLDER) to $DEST_DIR"
# Move the extracted folder to the final destination
if ! mv "$EXTRACTED_FOLDER" "$DEST_DIR/"; then
    echo "Error: Failed to move the extracted folder."
    exit 1
fi

# --- 4. Cleanup ---
echo "Cleaning up temporary download file: $TARGET_FILE"
rm -f "$TARGET_FILE"

echo "Script finished successfully. Please restart enigma2 manually"
