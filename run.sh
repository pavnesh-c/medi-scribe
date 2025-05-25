#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on a port
kill_port() {
    if check_port $1; then
        echo -e "${BLUE}Port $1 is in use. Attempting to kill the process...${NC}"
        lsof -ti :$1 | xargs kill -9
        sleep 2
    fi
}

# Kill any existing processes on ports 3000 and 5000
kill_port 3000
kill_port 5000

# Create necessary directories
mkdir -p backend/uploads
mkdir -p backend/logs

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up database
echo -e "${GREEN}Setting up database...${NC}"
export FLASK_APP=app
export FLASK_ENV=development
flask db upgrade

# Start Flask server
echo -e "${GREEN}Starting Flask server...${NC}"
flask run --port=5000 &
BACKEND_PID=$!

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd ../frontend
npm install
npm run dev &
FRONTEND_PID=$!

# Function to handle script termination
cleanup() {
    echo -e "\n${BLUE}Shutting down servers...${NC}"
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Set up trap for cleanup on script termination
trap cleanup SIGINT SIGTERM

# Keep script running
echo -e "${GREEN}Servers are running!${NC}"
echo -e "${BLUE}Backend: http://localhost:5000${NC}"
echo -e "${BLUE}Frontend: http://localhost:3000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the servers${NC}"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID 