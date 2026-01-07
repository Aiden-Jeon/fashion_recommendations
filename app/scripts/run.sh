#!/bin/bash

# Fashion Recommendations Dashboard - Run Script

echo "Starting Fashion Recommendations Dashboard..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
else
    # Activate virtual environment
    source .venv/bin/activate
fi

# Run the application
echo "Starting server on http://localhost:8000"
uvicorn app:app --reload --host "0.0.0.0"
