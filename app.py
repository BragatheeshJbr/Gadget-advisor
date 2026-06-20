import os
import streamlit as st
from groq import Groq

# ── Page configuration ─────────────────────────────────────────
st.set_page_config(
    page_title="Gadget Advisor",
    page_icon="🤖",
    layout="centered"
)

# ── Connect to Groq ────────────────────────────────────────────
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── The system prompt ──────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly and honest gadget buying advisor.
You help non-technical people — like doctors, teachers,
bank employees, and homemakers — buy the right
electronics and gadgets for their specific needs.

CONVERSATION RULES:
- Ask maximum 2 questions in one message before recommending.
- Never ask questions one by one — ask both together.
- Only recommend AFTER you have budget, use case, and preferences.
- Always search for live prices before giving a recommendation.

ALWAYS do this:
- Ask 2 questions maximum before recommending.
- Give ONE specific product recommendation, not a list.
- Explain in plain English — no tech jargon ever.
- Always say why this product fits their specific life.
- Always mention current price and where to buy it.

NEVER do this:
- Never recommend outside the user's stated budget.
- Never guess a price — always search for it first.
- Never recommend a product you are not confident exists.
- Never answer questions outside electronics and gadgets.
- Never make the user feel stupid for not knowing specs.
"""

# ── Page header ────────────────────────────────────────────────
st.title("🤖 Gadget Advisor")
st.caption("Your personal tech friend — live prices from Amazon & Flipkart.")
st.divider()

# ── Session memory ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome = "Hi! I'm your Gadget Advisor 👋 Tell me what you're looking to buy and I'll find the right one — with live prices!"
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome
    })

# ── Display conversation history ───────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ─────────────────────────────────────────────────
user_input = st.chat_input("Tell me what gadget you're looking for...")

if user_input:

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("assistant"):
        with st.spinner("Finding the best option with live prices..."):
            try:
                # ── Single API call with Groq built-in web search ──
                # No Tavily needed — Groq searches natively
                # Keep only last 6 messages to avoid context limit
                # 6 messages = 3 back and forth exchanges — enough
                # for a complete gadget recommendation conversation
                recent_messages = st.session_state.messages[-6:]

                response = client.chat.completions.create(
                    model="compound-beta",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + recent_messages,
                    max_tokens=1024
                )
                
                reply = response.choices[0].message.content

                # ── Show if web search was used ────────────────────
                if hasattr(response.choices[0].message, 'executed_tools'):
                    tools_used = response.choices[0].message.executed_tools
                    if tools_used:
                        st.caption("🔍 Searched live web for current prices")

                st.markdown(reply)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })