#!/bin/bash

# Deployment script for voidterminal.app

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of Void Terminal...${NC}"

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run with gunicorn
echo -e "${GREEN}Starting Void Terminal on port 5000...${NC}"
gunicorn --worker-class eventlet -w 1 --bind 127.0.0.1:5000 --timeout 120 --keep-alive 5 --log-level warning app:app