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

You have access to web search. Use it to find:
- Current prices on Amazon India and Flipkart
- Whether a product is currently available
- Recent reviews from the last 6 months

ALWAYS do this:
- Ask 2-3 short questions before recommending.
- Give ONE specific product recommendation, not a list.
- Explain in plain English — no tech jargon ever.
- Always say why this product fits their specific life.
- Search for the current price before mentioning it.
- Tell them exactly where to buy it with the price
  you found — Amazon or Flipkart.

NEVER do this:
- Never recommend outside the user's stated budget.
- Never guess a price — always search for it first.
- Never recommend a product you are not confident
  exists. Say 'I am not sure' instead.
- Never answer questions outside electronics and
  gadgets. Politely redirect.
- Never make the user feel stupid for not knowing
  technical specs.

If you are unsure about anything, say so clearly
rather than guessing.
"""

# ── Web search tool definition ─────────────────────────────────
# This tells Groq what tools the agent is allowed to use
# The agent reads this and decides when to use web search
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current prices, availability and reviews of electronics products on Amazon India and Flipkart",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — e.g. 'Samsung Galaxy Tab S6 Lite price Flipkart 2024'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── Page header ────────────────────────────────────────────────
st.title("🤖 Gadget Advisor")
st.caption("Your personal tech friend — tells you exactly what to buy, with live prices.")
st.divider()

# ── Session memory ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome = "Hi! I'm your Gadget Advisor 👋 Tell me what you're looking to buy and I'll find you the right one — with live prices from Amazon and Flipkart!"
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

    # Show user message
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("assistant"):
        with st.spinner("Searching for the best option and live prices..."):
            try:
                # ── First call — agent decides whether to search ───
                # We pass the tools list so agent knows it CAN search
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + st.session_state.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1024
                )

                message = response.choices[0].message

                # ── Check if agent wants to do a web search ────────
                # tool_calls means the agent decided to search
                if message.tool_calls:

                    # Get the search query the agent chose
                    search_query = message.tool_calls[0].function.arguments
                    
                    # Show user we are searching — transparency
                    st.caption(f"🔍 Searching: {search_query}")

                    # ── Second call — send search results back ─────
                    # Tell Groq to actually execute the search
                    # and give us the final answer with real data
                    final_response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT}
                        ] + st.session_state.messages + [
                            message,
                            {
                                "role": "tool",
                                "tool_call_id": message.tool_calls[0].id,
                                "content": search_query
                            }
                        ],
                        tools=TOOLS,
                        tool_choice="none",
                        max_tokens=1024
                    )

                    reply = final_response.choices[0].message.content

                else:
                    # Agent didn't need to search — just answer
                    # This happens for early questions like
                    # "what's your budget?" before recommending
                    reply = message.content

                st.markdown(reply)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

            except Exception as e:
                # ── Friendly error — not a raw technical crash ─────
                # This is the guardrail we talked about
                # Users see a human message, not a Python error
                friendly_msg = "I'm having a little trouble right now — please try again in a moment! 🙏"
                st.warning(friendly_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": friendly_msg
                })