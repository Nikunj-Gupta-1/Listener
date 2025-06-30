#!/bin/bash
# Install dependencies only

set -e

echo "Installing Python dependencies..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed successfully!"
