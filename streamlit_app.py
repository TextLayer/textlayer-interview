import streamlit as st
import requests
import pandas as pd
st.set_page_config(page_title="Financial Data Chat")
st.title("Chat with Your Financial Data")

# Initialize 
if "messages" not in st.session_state:
    st.session_state.messages = []

def show_response(response_text):
    """Display the response from the API - handles both formatted and plain text"""
    
    clean_text = response_text.replace('\\n', '\n')
    
    has_special_formatting = False
    formatting_tags = ["[EXPLANATION_START]", "[TABLE_START]", "[INSIGHTS_START]", "[NEXT_STEPS_START]"]
    
    for tag in formatting_tags:
        if tag in clean_text:
            has_special_formatting = True
            break
    
    if has_special_formatting:
        # Handle explanation section in the app
        if "[EXPLANATION_START]" in clean_text:
            explanation_part = clean_text.split("[EXPLANATION_START]")[1]
            explanation_text = explanation_part.split("[EXPLANATION_END]")[0]
            explanation_text = explanation_text.strip()
            st.write(explanation_text)
        
        # Handle table section in the app
        if "[TABLE_START]" in clean_text:
            table_part = clean_text.split("[TABLE_START]")[1]
            table_text = table_part.split("[TABLE_END]")[0]
            table_text = table_text.strip()
            
            all_lines = table_text.split('\n')
            table_lines = []
            
            for line in all_lines:
                line = line.strip()
                if line and '|' in line:
                    table_lines.append(line)
            
            if len(table_lines) >= 2:
                header_row = table_lines[0]
                header_parts = header_row.split('|')
                column_headers = []
                
                for part in header_parts:
                    clean_part = part.strip()
                    if clean_part:
                        column_headers.append(clean_part)
                
                data_rows = []
                for i in range(2, len(table_lines)):  
                    data_row = table_lines[i]
                    row_parts = data_row.split('|')
                    clean_row = []
                    
                    for part in row_parts:
                        clean_part = part.strip()
                        if clean_part:
                            clean_row.append(clean_part)
                    
                    if clean_row:
                        data_rows.append(clean_row)
                
                if column_headers and data_rows:
                    try:
                        df = pd.DataFrame(data_rows, columns=column_headers)
                        st.dataframe(df, use_container_width=True)
                    except:
                        st.text(table_text)
        
        if "[INSIGHTS_START]" in clean_text:
            insights_part = clean_text.split("[INSIGHTS_START]")[1]
            insights_text = insights_part.split("[INSIGHTS_END]")[0]
            insights_text = insights_text.strip()
            st.subheader("Key Insights")
            st.write(insights_text)
        
        if "[NEXT_STEPS_START]" in clean_text:
            steps_part = clean_text.split("[NEXT_STEPS_START]")[1]
            steps_text = steps_part.split("[NEXT_STEPS_END]")[0]
            steps_text = steps_text.strip()
            st.subheader("Next Steps")
            st.write(steps_text)
    
    else:
        st.write(clean_text)

# Show all previous messages
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["content"])
    else:
        with st.chat_message("assistant"):
            show_response(message["content"])

user_input = st.chat_input("Ask about your data...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    with st.chat_message("assistant"):
        with st.spinner("Processing your question..."):
            try:
                # Call the API
                api_response = requests.post(
                    "http://localhost:5000/v1/threads/chat",
                    json={"messages": [{"role": "user", "content": user_input}]}
                )
                
                response_data = api_response.json()
                assistant_message = response_data["payload"][-1]["content"]
                
                show_response(assistant_message)
                
                # chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": assistant_message
                })
                
            except Exception as error:
                error_message = f"Something went wrong: {str(error)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })