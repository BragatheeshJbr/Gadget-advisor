import os
import json
import streamlit as st
from groq import Groq
from tavily import TavilyClient

# ── Page configuration ─────────────────────────────────────────
st.set_page_config(
    page_title="Gadget Advisor",
    page_icon="🤖",
    layout="centered"
)

# ── Connect to Groq and Tavily ─────────────────────────────────
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

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

# ── Tool definition — tells Groq what tools exist ─────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current prices and availability of electronics on Amazon India and Flipkart",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query e.g. 'Samsung Galaxy Tab S6 Lite price Flipkart India 2024'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── The actual search function — this does the real work ───────
# This is what runs when the agent decides to search
# Tavily searches the web and returns clean results
def web_search(query):
    try:
        results = tavily.search(
            query=query,
            search_depth="basic",
            max_results=3
        )
        # Pull out just the useful text from results
        output = ""
        for r in results.get("results", []):
            output += f"Source: {r['url']}\n"
            output += f"Info: {r['content']}\n\n"
        return output if output else "No results found."
    except Exception as e:
        return f"Search failed: {e}"

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
                # ── Step 1: Ask Groq what to do ───────────────────
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

                # ── Step 2: If agent wants to search, do it ───────
                if message.tool_calls:
                    tool_call = message.tool_calls[0]

                    # Get the query the agent chose
                    args = json.loads(tool_call.function.arguments)
                    query = args["query"]

                    # Show user what we're searching
                    st.caption(f"🔍 Searching live: {query}")

                    # Actually run the search using Tavily
                    search_results = web_search(query)

                    # ── Step 3: Send results back to Groq ─────────
                    # Now Groq reads the real search results
                    # and writes the final recommendation
                    final_response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT}
                        ] + st.session_state.messages + [
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": message.tool_calls
                            },
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": search_results
                            }
                        ],
                        max_tokens=1024
                    )

                    reply = final_response.choices[0].message.content

                else:
                    # No search needed — just answer directly
                    reply = message.content

                st.markdown(reply)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

            except Exception as e:
                friendly_msg = "I'm having a little trouble right now — please try again in a moment! 🙏"
                st.warning(friendly_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": friendly_msg
                })