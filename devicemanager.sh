REPO_OWNER="ahmedmoselhi"
REPO_NAME="enigma2-plugins-miscellaneous"
FILE_PREFIX="DeviceManager"
DOWNLOAD_DIR="/var/volatile/tmp"
DEST_DIR="/usr/lib/enigma2/python/Plugins/SystemPlugins"
API_URL="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/"

echo "1. Searching for the correct archive name..."
# *** FIX: Using standard grep and cut/sed instead of 'grep -P' ***
ARCHIVE_NAME=$(curl -s "$API_URL" | grep -o '"name": "[^"]*'"$FILE_PREFIX"'.*\.tar\.gz"' | head -n 1 | sed -e 's/.*"name": "//' -e 's/"$//')

if [ -z "$ARCHIVE_NAME" ]; then
    echo "Error: Could not find any file starting with '$FILE_PREFIX' and ending with '.tar.gz'"
    exit 1
fi

echo "Found file: $ARCHIVE_NAME"
TARGET_FILE="${DOWNLOAD_DIR}/${ARCHIVE_NAME}"
DOWNLOAD_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/master/${ARCHIVE_NAME}"
EXTRACTED_FOLDER="${DOWNLOAD_DIR}/${FILE_PREFIX}" # Still assume extracted folder is just 'DeviceManager'
echo "Attempting to download $ARCHIVE_NAME..."
mkdir -p "$DOWNLOAD_DIR"
if ! wget -O "$TARGET_FILE" "$DOWNLOAD_URL"; then
    echo "Error: Failed to download the file from $DOWNLOAD_URL"
    exit 1
fi

echo "Download successful to $TARGET_FILE"
if [ -d "$DEST_DIR/$FILE_PREFIX" ]; then
    echo "Removing existing destination folder: $DEST_DIR/$FILE_PREFIX"
    rm -rf "$DEST_DIR/$FILE_PREFIX"
fi
mkdir -p "$DEST_DIR"

echo "Extracting the archive..."
if ! tar -xzf "$TARGET_FILE" -C "$DOWNLOAD_DIR"; then
    echo "Error: Failed to extract the archive $TARGET_FILE"
    exit 1
fi

echo "Moving the extracted folder ($EXTRACTED_FOLDER) to $DEST_DIR"
if ! mv "$EXTRACTED_FOLDER" "$DEST_DIR/"; then
    echo "Error: Failed to move the extracted folder."
    exit 1
fi
echo "Cleaning up temporary download file: $TARGET_FILE"
rm -f "$TARGET_FILE"

echo "Script finished successfully. Please restart enigma2 manually"