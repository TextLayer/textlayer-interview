#!/bin/bash

# TextLayer Financial AI Assistant Startup Script
echo "🚀 Starting TextLayer Financial AI Assistant..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Doppler token is set
if [ -z "$DOPPLER_TOKEN" ]; then
    echo -e "${RED}❌ DOPPLER_TOKEN environment variable is not set${NC}"
    echo -e "${YELLOW}💡 Please run: export DOPPLER_TOKEN=dp.st.prd.ZSiWlMjSmwiSLkGWu5fwJOYstT9x1EgqVSMy8mIEYA6${NC}"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    kill $FLASK_PID 2>/dev/null
    kill $STREAMLIT_PID 2>/dev/null
    # Also kill any remaining processes on these ports
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Services stopped${NC}"
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM

# Kill any existing processes on our ports
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
pkill -f "flask.*run" 2>/dev/null || true
pkill -f "streamlit.*run" 2>/dev/null || true
lsof -ti:5001 | xargs kill -9 2>/dev/null || true  
lsof -ti:8501 | xargs kill -9 2>/dev/null || true
sleep 2

# Start Flask API in the background
echo -e "${BLUE}🔧 Starting Flask API server...${NC}"
doppler run -- .venv/bin/python -m flask --app application run --host=0.0.0.0 --port=5001 --debug > flask.log 2>&1 &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 3

# Check if Flask started successfully
if kill -0 $FLASK_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Flask API server started (PID: $FLASK_PID)${NC}"
    echo -e "${GREEN}   🌐 API available at: http://localhost:5001${NC}"
else
    echo -e "${RED}❌ Failed to start Flask API server${NC}"
    echo -e "${YELLOW}💡 Check flask.log for details${NC}"
    exit 1
fi

# Start Streamlit in the background
echo -e "${BLUE}🎨 Starting Streamlit web interface...${NC}"
echo "" | .venv/bin/streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true > streamlit.log 2>&1 &
STREAMLIT_PID=$!

# Wait a moment for Streamlit to start
sleep 5

# Check if Streamlit started successfully
if kill -0 $STREAMLIT_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Streamlit web interface started (PID: $STREAMLIT_PID)${NC}"
    echo -e "${GREEN}   🌐 Web interface available at: http://localhost:8501${NC}"
else
    echo -e "${RED}❌ Failed to start Streamlit web interface${NC}"
    echo -e "${YELLOW}💡 Check streamlit.log for details${NC}"
    cleanup
    exit 1
fi

echo -e "\n${GREEN}🎉 TextLayer Financial AI Assistant is ready!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🌐 Web Interface: http://localhost:8501${NC}"
echo -e "${GREEN}🔧 API Endpoints: http://localhost:5001${NC}"
echo -e "${GREEN}   • Linear Chat:  POST /v1/threads/chat${NC}"
echo -e "${GREEN}   • Agentic Chat: POST /v1/threads/chat/agentic${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}💡 Press Ctrl+C to stop all services${NC}"

# Keep the script running and wait for processes
wait
