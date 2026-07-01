import os
import re
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

# ── System prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly gadget buying advisor for non-technical people.

STEPS:
1. If you don't know their use case or brand preference — ask both in ONE message.
2. Once you have budget + use case — use web_search to find price then recommend ONE product.

RULES:
- Never recommend before understanding their need
- Never exceed their budget
- No tech jargon — plain English only
- Never go outside electronics topic
- Always search for live price before recommending
- Keep replies short and clear
- One recommendation only — not a list"""

# ── Tool definition ────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search for current prices of electronics on Amazon India and Flipkart. Use only when ready to recommend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query e.g. 'Samsung phone under 20000 Flipkart India 2024'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── Real web search via Tavily ─────────────────────────────────
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

# ── Context extraction ─────────────────────────────────────────
# Pulls key facts out of each message
# Keeps request size tiny — prevents 413 permanently
def extract_context(user_message):
    msg = user_message.lower()

    budget_match = re.search(r'(\d[\d,]*)\s*(?:rupees|rs|₹|inr)?', msg)
    if budget_match and not st.session_state.context["budget"]:
        amount = budget_match.group(1).replace(",", "")
        if int(amount) > 1000:
            st.session_state.context["budget"] = f"₹{amount}"

    gadgets = ["phone", "mobile", "tablet", "laptop", "earphone",
               "earbuds", "tv", "television", "camera", "watch",
               "smartwatch", "speaker", "headphone"]
    for g in gadgets:
        if g in msg and not st.session_state.context["gadget"]:
            st.session_state.context["gadget"] = g
            break

    uses = ["camera", "calls", "gaming", "study", "work", "music",
            "video", "social media", "photos", "teaching", "reading"]
    found_uses = [u for u in uses if u in msg]
    if found_uses and not st.session_state.context["use_case"]:
        st.session_state.context["use_case"] = ", ".join(found_uses)

    brands = ["samsung", "redmi", "xiaomi", "realme", "oppo", "vivo",
              "oneplus", "apple", "nokia", "motorola", "poco"]
    for b in brands:
        if b in msg and not st.session_state.context["brand"]:
            st.session_state.context["brand"] = b
            break
    if any(x in msg for x in ["no preference", "any brand", "no brand", "anything"]):
        st.session_state.context["brand"] = "no preference"

# ── Build context summary ──────────────────────────────────────
def build_context_message():
    ctx = st.session_state.context
    parts = []
    if ctx["gadget"]: parts.append(f"Gadget: {ctx['gadget']}")
    if ctx["budget"]: parts.append(f"Budget: {ctx['budget']}")
    if ctx["use_case"]: parts.append(f"Use case: {ctx['use_case']}")
    if ctx["brand"]: parts.append(f"Brand: {ctx['brand']}")
    if parts:
        return "User info collected so far: " + " | ".join(parts)
    return ""

# ── Page header ────────────────────────────────────────────────
st.title("🤖 Gadget Advisor")
st.caption("Your personal tech friend — live prices from Amazon & Flipkart.")
st.divider()

# ── Session state setup ────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.context = {
        "gadget": None, "budget": None,
        "use_case": None, "brand": None
    }
    welcome = "Hi! I'm your Gadget Advisor 👋 Tell me what gadget you're looking for and your budget — I'll find the perfect one for you!"
    st.session_state.messages.append({
        "role": "assistant", "content": welcome
    })

# ── Reset button ───────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Reset"):
        st.session_state.messages = []
        st.session_state.context = {
            "gadget": None, "budget": None,
            "use_case": None, "brand": None
        }
        st.rerun()

# ── Display conversation ───────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ─────────────────────────────────────────────────
user_input = st.chat_input("Tell me what gadget you're looking for...")

if user_input:

    extract_context(user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user", "content": user_input
    })

    with st.chat_message("assistant"):
        with st.spinner("Finding the best option..."):
            try:
                # Build messages — system prompt + context + last 2 messages
                # Keeps request size small — no 413 ever
                context_summary = build_context_message()
                recent = st.session_state.messages[-2:]

                messages_to_send = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ]
                if context_summary:
                    messages_to_send.append({
                        "role": "system", "content": context_summary
                    })
                messages_to_send.extend(recent)

                # ── First call — does agent want to search? ────────
                response = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=messages_to_send,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=400
                )

                message_obj = response.choices[0].message

                # ── If agent wants to search ───────────────────────
                if message_obj.tool_calls:
                    tool_call = message_obj.tool_calls[0]

                    try:
                        args = json.loads(tool_call.function.arguments)
                        query = args.get("query", "")
                    except Exception:
                        query = ""

                    if query:
                        st.caption(f"🔍 Searching: {query}")
                        search_results = web_search(query)

                        # ── Second call with search results ────────
                        final_response = client.chat.completions.create(
                            model="qwen/qwen3.6-27b",
                            messages=messages_to_send + [
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
                            max_tokens=400
                        )
                        reply = final_response.choices[0].message.content
                    else:
                        reply = message_obj.content or "Could you tell me more about what you need?"

                else:
                    # No search needed — direct answer
                    reply = message_obj.content or "Could you tell me more about what you need?"

                st.markdown(reply)
                st.session_state.messages.append({
                    "role": "assistant", "content": reply
                })

            except Exception as e:
                error_str = str(e).lower()

                if "429" in error_str or "rate limit" in error_str:
                    msg = "I'm helping a lot of people right now — please try again in 30 seconds! 😊"
                elif "401" in error_str:
                    msg = "I'm having a technical issue. Please try again in a moment."
                elif "503" in error_str:
                    msg = "Service is temporarily busy. Please try again! 🙏"
                else:
                    msg = "Something went wrong. Please try again or click Reset to start fresh."

                st.markdown(msg)
                st.session_state.messages.append({
                    "role": "assistant", "content": msg
                })