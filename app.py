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

STRICT CONVERSATION RULES:
- First message: ONLY ask what they want to buy if not clear.
- Ask ALL your questions in ONE single message — not one by one.
- Ask maximum 2 questions at once. Never more.
- ONLY search the web AFTER you have collected all the 
  information you need to make a recommendation.
- Never search in the middle of asking questions.
- Once you have enough information, search ONCE and recommend.

ALWAYS do this:
- Ask 2 questions maximum before recommending.
- Give ONE specific product recommendation, not a list.
- Explain in plain English — no tech jargon ever.
- Always say why this product fits their specific life.
- Search for the current price before mentioning it.
- Tell them exactly where to buy with the price you found.

NEVER do this:
- Never recommend outside the user's stated budget.
- Never guess a price — always search for it first.
- Never recommend a product you are not confident exists.
- Never answer questions outside electronics and gadgets.
- Never make the user feel stupid for not knowing specs.
- Never show raw search queries or function calls to the user.
- Never search before you have enough information to recommend.

If you are unsure about anything, say so clearly
rather than guessing.
"""

# ── Tool definition ────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search for current prices and availability of electronics on Amazon India and Flipkart. Only use this when you are ready to make a final recommendation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query e.g. 'Oppo A17 price Flipkart India 2024'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── Real web search function ───────────────────────────────────
def web_search(query):
    try:
        results = tavily.search(
            query=query,
            search_depth="basic",
            max_results=3
        )
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
        with st.spinner("Thinking..."):
            try:
                # ── Step 1: First call to Groq ─────────────────────
                response = client.chat.completions.create(
                    model="llama3-groq-70b-8192-tool-use-preview",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + st.session_state.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1024
                )

                message_obj = response.choices[0].message

                # ── Step 2: Check if agent wants to search ─────────
                if message_obj.tool_calls:

                    tool_call = message_obj.tool_calls[0]

                    # Safely parse the arguments
                    try:
                        args = json.loads(tool_call.function.arguments)
                        query = args.get("query", "")
                    except Exception:
                        query = ""

                    if query:
                        # Show searching indicator
                        st.caption(f"🔍 Searching: {query}")

                        # Run the actual search
                        search_results = web_search(query)

                        # ── Step 3: Send results back to Groq ─────
                        final_response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT}
                            ] + st.session_state.messages + [
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": tool_call.id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_call.function.name,
                                                "arguments": tool_call.function.arguments
                                            }
                                        }
                                    ]
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
                        # Query was empty — just answer directly
                        reply = message_obj.content or "Could you tell me more about what you're looking for?"

                else:
                    # No search needed — agent answers directly
                    reply = message_obj.content or "Could you tell me more about what you're looking for?"

                # ── Step 4: Show reply and save to history ─────────
                if reply:
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