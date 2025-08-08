#!/bin/bash

# Start Flask API in background on port 5001
echo "🚀 Starting Flask API server in background..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Doppler token is set
if [ -z "$DOPPLER_TOKEN" ]; then
    echo -e "${RED}❌ DOPPLER_TOKEN environment variable is not set${NC}"
    echo -e "${YELLOW}💡 Please run: export DOPPLER_TOKEN=dp.st.prd.ZSiWlMjSmwiSLkGWu5fwJOYstT9x1EgqVSMy8mIEYA6${NC}"
    exit 1
fi

# Kill any existing processes on port 5001
echo -e "${YELLOW}🧹 Cleaning up existing processes on port 5001...${NC}"
pkill -f "flask.*run" 2>/dev/null || true
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
sleep 2

# Start Flask API in the background
echo -e "${YELLOW}🔧 Starting Flask API server in background...${NC}"
doppler run -- .venv/bin/python -m flask --app application run --host=0.0.0.0 --port=5001 --debug > flask.log 2>&1 &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 3

# Check if Flask started successfully
if kill -0 $FLASK_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Flask API server started in background (PID: $FLASK_PID)${NC}"
    echo -e "${GREEN}   🌐 API available at: http://localhost:5001${NC}"
    echo -e "${GREEN}   📊 Health check: curl http://localhost:5001/v1/health${NC}"
    echo -e "${GREEN}   📝 Logs: tail -f flask.log${NC}"
    echo -e "${YELLOW}   🛑 To stop: kill $FLASK_PID${NC}"
else
    echo -e "${RED}❌ Failed to start Flask API server${NC}"
    echo -e "${YELLOW}💡 Check flask.log for details${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 Flask API is running in the background!${NC}"
