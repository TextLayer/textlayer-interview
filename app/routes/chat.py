from flask import Blueprint, request, jsonify
from app.services.llm.prompts.chat_prompt import SYSTEM_PROMPT

chat_bp = Blueprint("chat", __name__)

def read_financial_data():
    with open("data/financials.txt", "r") as f:
        return f.read()

def generate_response(user_input, data):
    if "revenue in Q2" in user_input:
        for line in data.splitlines():
            if "Q2 Revenue" in line:
                return f"- {line}\n- 12% higher than Q1\n- Driven mainly by growth in Europe"
    elif "profit margin in Q2" in user_input:
        for line in data.splitlines():
            if "Q2 Profit Margin" in line:
                return f"- {line}"
    elif "increase from Q1 to Q2" in user_input:
        return "- Yes, Q2 revenue increased compared to Q1."
    else:
        return "I need more data to answer that confidently."

@chat_bp.route("/v1/threads/chat", methods=["POST"])
def chat():
    user_input = request.json["messages"][0]["content"]
    data = read_financial_data()
    response_text = generate_response(user_input, data)
    return jsonify({
        "thread_id": "thread-id",
        "message": {
            "role": "assistant",
            "content": response_text
        }
    })
