import os
import streamlit as st
from groq import Groq

# ── Page configuration ─────────────────────────────────────────
# This sets up how the web page looks in the browser
st.set_page_config(
    page_title="Gadget Advisor",
    page_icon="🤖",
    layout="centered"
)

# ── Connect to Groq ────────────────────────────────────────────
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── The system prompt — same brain as before ──────────────────
SYSTEM_PROMPT = """
You are a friendly and honest gadget buying advisor.
You help non-technical people — like doctors, teachers,
bank employees, and homemakers — buy the right
electronics and gadgets for their specific needs.

ALWAYS do this:
- Ask 2-3 short questions before recommending.
- Give ONE specific product recommendation, not a list.
- Explain in plain English — no tech jargon ever.
- Always say why this product fits their specific life.
- Mention where to buy it (Amazon, Flipkart).

NEVER do this:
- Never recommend outside the user's stated budget.
- Never state a price as exact. Always say
  'approximately' or 'check current price'.
- Never recommend a product you are not confident
  exists. Say 'I am not sure' instead.
- Never answer questions outside electronics and
  gadgets. Politely redirect.
- Never make the user feel stupid for not knowing
  technical specs.

If you are unsure about anything, say so clearly
rather than guessing.
"""

# ── Page header ────────────────────────────────────────────────
st.title("🤖 Gadget Advisor")
st.caption("Your personal tech friend — tells you exactly what to buy, in plain English.")
st.divider()

# ── Session memory ─────────────────────────────────────────────
# st.session_state is Streamlit's way of remembering things
# across messages — like our conversation_history list before
# Every time user sends a message, Streamlit reruns the whole
# script — session_state makes sure history isn't wiped
if "messages" not in st.session_state:
    st.session_state.messages = []

    # Greet the user on first load
    welcome = "Hi! I'm your Gadget Advisor 👋 Tell me what you're looking to buy and I'll help you find exactly the right one for your needs — no confusing tech specs, I promise!"
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome
    })

# ── Display full conversation history ─────────────────────────
# Loop through every message and display it as a chat bubble
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input box at the bottom ──────────────────────────────
# st.chat_input creates the text box at the bottom of the screen
user_input = st.chat_input("Tell me what gadget you're looking for...")

if user_input:

    # Show the user's message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Add to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    # Send full conversation to Groq
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + st.session_state.messages,
                    max_tokens=1024
                )

                reply = response.choices[0].message.content
                st.markdown(reply)

                # Add agent reply to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

            except Exception as e:
                error_msg = "Sorry, something went wrong. Please try again in a moment."
                st.error(error_msg)