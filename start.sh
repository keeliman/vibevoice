#!/bin/bash
# Start script for vibevoice - M1 Mac optimized version

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    .venv/bin/pip install -r requirements.txt
    echo ""
    echo "Installing vibevoice package..."
    .venv/bin/pip install -e .
    echo ""
    echo "Installation complete!"
else
    # Ensure package is installed (in case it was removed)
    if ! .venv/bin/python -c "import vibevoice" 2>/dev/null; then
        echo "Installing vibevoice package..."
        .venv/bin/pip install -e .
        echo ""
    fi
fi

# Activate virtual environment and run vibevoice
echo "Starting vibevoice..."
echo ""
.venv/bin/python -m vibevoice.cli
