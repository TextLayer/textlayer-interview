import streamlit as st
import requests
import json
import time
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="TextLayer Financial AI Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #4f46e5;
    }
    .user-message {
        background-color: #f1f5f9;
        border-left-color: #3b82f6;
    }
    .assistant-message {
        background-color: #f0fdf4;
        border-left-color: #10b981;
    }
    .error-message {
        background-color: #fef2f2;
        border-left-color: #ef4444;
        color: #dc2626;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    }
    .stButton > button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>💰 TextLayer Financial AI Assistant</h1>
    <p>Ask questions about your financial data in natural language</p>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # API endpoint selection
    api_base_url = st.text_input(
        "API Base URL", 
        value="http://localhost:5001",
        help="Base URL for the TextLayer API"
    )
    
    # Analysis mode selection
    analysis_mode = st.radio(
        "Analysis Mode",
        ["🤖 Agentic AI (Multi-Agent)", "⚡ Linear Processing"],
        help="Choose between multi-agent analysis or simple linear processing"
    )
    
    st.markdown("---")
    
    # Sample queries
    st.markdown("### 💡 Sample Queries")
    
    sample_queries = [
        "What is the total revenue for 2018?",
        "Compare Q1 vs Q2 performance",
        "Which regions performed best this year?",
        "Show me monthly revenue trends",
        "Compare actual vs budget performance",
        "What are the top performing products?",
        "Analyze gross margin by quarter",
        "Show customer performance trends"
    ]
    
    for i, query in enumerate(sample_queries):
        if st.button(f"📊 {query}", key=f"sample_{i}"):
            st.session_state.sample_query = query

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Helper functions
def call_api(query: str, mode: str, base_url: str) -> dict:
    """Call the TextLayer API with the user query"""
    try:
        endpoint = "/v1/threads/chat/agentic" if "Agentic" in mode else "/v1/threads/chat"
        url = f"{base_url.rstrip('/')}{endpoint}"
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Make the API call
        response = requests.post(url, json=payload, headers=headers, timeout=60)
            
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API returned status {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The analysis is taking longer than expected."}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to API at {base_url}. Please check if the server is running."}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

def format_response(response_data: dict) -> str:
    """Format the API response for display"""
    if "error" in response_data:
        return f"❌ **Error**: {response_data['error']}"
    
    try:
        payload = response_data.get("payload", [])
        if isinstance(payload, list) and len(payload) > 0:
            # Get the last assistant message
            for message in reversed(payload):
                if message.get("role") == "assistant" and message.get("content"):
                    return message["content"]
        
        return "No response content found."
        
    except Exception as e:
        return f"Error formatting response: {str(e)}"

def display_message(role: str, content: str, timestamp: str = None):
    """Display a chat message with proper styling"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S")
    
    css_class = "user-message" if role == "user" else "assistant-message"
    icon = "👤" if role == "user" else "🤖"
    
    st.markdown(f"""
    <div class="chat-message {css_class}">
        <strong>{icon} {role.title()}</strong> <small style="color: #6b7280;">({timestamp})</small><br>
        {content}
    </div>
    """, unsafe_allow_html=True)

# Main chat interface
st.markdown("### 💬 Chat Interface")

# Display chat history
for message in st.session_state.messages:
    display_message(
        message["role"], 
        message["content"], 
        message.get("timestamp", "")
    )

# Chat input using form for better handling
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([6, 1])
    
    with col1:
        # Check if there's a sample query to use
        default_query = ""
        if "sample_query" in st.session_state:
            default_query = st.session_state.sample_query
            del st.session_state.sample_query

        user_query = st.text_input(
            "Ask a question about your financial data:",
            value=default_query,
            placeholder="e.g., What is the total revenue for 2018?",
            label_visibility="visible"
        )

    with col2:
        st.write("")  # Add some space
        st.write("")  # Add more space to align with input
        send_button = st.form_submit_button(
            "Send 🚀",
            use_container_width=True
        )

# Process user input
if send_button and user_query and user_query.strip():
    # Store the query before processing
    query_to_process = user_query.strip()
    
    # Debug information
    st.write(f"🐛 Debug: Query = '{query_to_process}'")
    st.write(f"🐛 Debug: Mode = '{analysis_mode}'")
    st.write(f"🐛 Debug: API URL = '{api_base_url}'")
    
    # Add user message to history
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "user",
        "content": query_to_process,
        "timestamp": timestamp
    })
    
    # Display the user message immediately
    display_message("user", query_to_process, timestamp)
    
    # Call API and get response
    with st.spinner(f"🤔 Analyzing with {analysis_mode}..."):
        response = call_api(query_to_process, analysis_mode, api_base_url)
    
    # Debug API response
    st.write(f"🐛 Debug: API Response = {response}")
    
    # Format and add assistant response
    assistant_response = format_response(response)
    assistant_timestamp = datetime.now().strftime("%H:%M:%S")
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_response,
        "timestamp": assistant_timestamp,
        "mode": analysis_mode
    })
    
    # Display the assistant response
    display_message("assistant", assistant_response, assistant_timestamp)
    
    # Rerun to show the updated conversation
    st.rerun()

# Chat controls
if st.session_state.messages:
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("📄 Export Chat", use_container_width=True):
            # Create export data
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "mode": analysis_mode,
                "messages": st.session_state.messages
            }
            
            st.download_button(
                label="💾 Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"textlayer_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

# Footer with stats
if st.session_state.messages:
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    total_messages = len(st.session_state.messages)
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
    assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>💬</h3>
            <p><strong>{}</strong><br>Total Messages</p>
        </div>
        """.format(total_messages), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>👤</h3>
            <p><strong>{}</strong><br>User Queries</p>
        </div>
        """.format(user_messages), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>🤖</h3>
            <p><strong>{}</strong><br>AI Responses</p>
        </div>
        """.format(assistant_messages), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>⚙️</h3>
            <p><strong>{}</strong><br>Current Mode</p>
        </div>
        """.format(analysis_mode.split()[0]), unsafe_allow_html=True)

# Help section
with st.expander("ℹ️ Help & Tips"):
    st.markdown("""
    ### How to use this Financial AI Assistant:
    
    **🎯 Ask Natural Language Questions:**
    - "What is the total revenue for 2018?"
    - "Compare Q1 vs Q2 performance"
    - "Which customers are performing best?"
    - "Show me trends in gross margin"
    
    **🤖 Analysis Modes:**
    - **Agentic AI**: Uses multiple specialized agents for comprehensive analysis with business insights
    - **Linear Processing**: Simple query-to-response processing
    
    **💡 Tips:**
    - Be specific about time periods (e.g., "2018", "Q1", "monthly")
    - Ask for comparisons to get deeper insights
    - Use the sample queries to get started
    - Try both analysis modes to see the difference
    
    **⚙️ Database Schema:**
    - Financial data from 2018 with actual, budget, and forecast versions
    - Dimensions: Account, Customer, Product, Time, Version
    - Metrics: Revenue, expenses, margins by various breakdowns
    """)

# Debug information (can be removed in production)
with st.expander("🔧 Debug Information", expanded=False):
    st.write("**Session State:**", dict(st.session_state))
    st.write("**Analysis Mode:**", analysis_mode)
    st.write("**API Base URL:**", api_base_url)
    st.write("**Total Messages:**", len(st.session_state.messages))

# Status indicator
st.markdown(f"""
<div style="position: fixed; top: 10px; right: 10px; background: green; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.8rem; z-index: 999;">
    ● Ready
</div>
""", unsafe_allow_html=True)
