#!/bin/bash
# Build Labrynth UI and copy to server package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
UI_DIR="$ROOT_DIR/ui"
SERVER_UI_DIR="$ROOT_DIR/src/labrynth/server/ui"

echo "Building Labrynth UI..."
echo "UI source: $UI_DIR"
echo "Output: $SERVER_UI_DIR"
echo ""

# Check if UI directory exists
if [ ! -d "$UI_DIR" ]; then
    echo "Error: UI directory not found at $UI_DIR"
    exit 1
fi

# Navigate to UI directory
cd "$UI_DIR"

# Install dependencies
echo "Installing dependencies..."
npm ci

# Build
echo "Building production bundle..."
npm run build

# Remove old UI build
echo "Cleaning old build..."
rm -rf "$SERVER_UI_DIR"

# Copy new build
echo "Copying build to server..."
cp -r dist "$SERVER_UI_DIR"

echo ""
echo "UI built successfully!"
echo "Files copied to: $SERVER_UI_DIR"
echo ""
echo "To test: labrynth server start"
echo "UI will be available at: http://localhost:8000/"
