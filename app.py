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

# ── System prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly gadget buying advisor for non-technical people.

FOLLOW THESE STEPS STRICTLY:

STEP 1 - Ask BOTH these questions together in one message:
- "What will you use it for most?"
- "Any brand preference?"

STEP 2 - Only AFTER they answer, search and recommend.

STEP 3 - Give ONE product. Plain English. No jargon.
Say the price and where to buy (Amazon/Flipkart).

EXAMPLE:
User: "I want a phone under 15000"
You: "Great! Two quick questions:
1. What will you use it for — calls, camera, or social media?
2. Any brand preference like Samsung or Redmi?"
User: "Camera and calls. No preference."
You: [search then recommend ONE product with price]

RULES:
- NEVER recommend before asking Step 1 questions
- NEVER exceed user's budget
- NEVER use tech jargon — explain in simple words
- NEVER recommend outside electronics/gadgets
- NEVER guess prices — always search first
- Always explain why this product fits their life
- Keep responses concise and to the point
"""

# ── Smart message trimmer ──────────────────────────────────────
# This is the key function that prevents 413 errors
# It keeps trimming history until the request fits
# Think of it like a smart suitcase that fits everything in
def get_safe_messages(messages, max_messages=4):
    # Start with last 4 messages
    # If that's still too big, try 2
    # If that's still too big, try just the last 1
    # This way we never crash — we always send something
    for count in [max_messages, 2, 1]:
        recent = messages[-count:] if len(messages) >= count else messages
        # Rough token estimate — each word is about 1.3 tokens
        # System prompt + messages should stay under 3000 tokens
        total_chars = len(SYSTEM_PROMPT)
        for m in recent:
            total_chars += len(m.get("content", ""))
        # 3000 tokens ≈ 12000 characters — safe limit for compound-beta
        if total_chars < 12000:
            return recent
    # Absolute fallback — just the last message
    return messages[-1:]

# ── Friendly messages for every error type ─────────────────────
# Users never see technical errors — only human messages
def get_friendly_error(error_str):
    error_str = error_str.lower()

    if "413" in error_str or "too large" in error_str:
        return "Let me start fresh to give you a better answer. What gadget are you looking for and what's your budget?"

    elif "429" in error_str or "rate limit" in error_str:
        return "I'm helping a lot of people right now — please try again in about 30 seconds! 😊"

    elif "401" in error_str or "api_key" in error_str:
        return "I'm having a technical issue on my end. Please try again in a moment."

    elif "400" in error_str or "tool_use_failed" in error_str:
        return "I had trouble searching for that. Could you rephrase your request? For example: 'I want a phone under ₹15,000 for calling and camera.'"

    elif "503" in error_str or "unavailable" in error_str:
        return "The service is temporarily busy. Please try again in a minute! 🙏"

    else:
        return "Something went wrong on my end. Please try again — and if it keeps happening, try refreshing the page."

# ── Page header ────────────────────────────────────────────────
st.title("🤖 Gadget Advisor")
st.caption("Your personal tech friend — live prices from Amazon & Flipkart.")
st.divider()

# ── Session memory ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome = "Hi! I'm your Gadget Advisor 👋 Tell me what gadget you're looking for and your budget — I'll find the perfect one for you!"
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome
    })

# ── Reset button — gives user a clean start ────────────────────
# This is a soft kill switch — clears everything and starts over
if len(st.session_state.messages) > 6:
    if st.button("🔄 Start new search"):
        st.session_state.messages = []
        st.rerun()

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
        with st.spinner("Finding the best option..."):
            try:
                # Get safe trimmed history — never too large
                safe_messages = get_safe_messages(st.session_state.messages)

                response = client.chat.completions.create(
                    model="compound-beta",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + safe_messages,
                    max_tokens=512
                )

                reply = response.choices[0].message.content

                # Show search indicator if web was used
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
                # ── Never show raw error to user ───────────────────
                # Get the friendly version of whatever went wrong
                friendly = get_friendly_error(str(e))
                st.markdown(friendly)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": friendly
                })

                # ── Auto recovery for 413 errors ───────────────────
                # If request was too large, trim history automatically
                # and retry once — user never knows this happened
                if "413" in str(e) or "too large" in str(e).lower():
                    try:
                        # Retry with just 1 message
                        retry_response = client.chat.completions.create(
                            model="compound-beta",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                st.session_state.messages[-1]
                            ],
                            max_tokens=512
                        )
                        retry_reply = retry_response.choices[0].message.content
                        # Replace the error message with actual reply
                        st.session_state.messages[-1] = {
                            "role": "assistant",
                            "content": retry_reply
                        }
                        st.rerun()
                    except Exception:
                        # Retry also failed — friendly message stays
                        pass