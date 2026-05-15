import os
from groq import Groq

# ── STEP 1: Connect to Groq using your API key ────────────────────
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── STEP 2: The system prompt — the brain of your agent ──────────
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

# ── STEP 3: Store conversation history ───────────────────────────
# This is how the agent remembers the full conversation
# Every message — yours and the agent's — gets added here
conversation_history = []

# ── STEP 4: The agent loop ────────────────────────────────────────
print("\n🤖 Gadget Advisor — Your Personal Tech Friend")
print("─────────────────────────────────────────────")
print("Tell me what gadget you're looking for.")
print("Type 'quit' to exit.\n")

while True:

    # Get input from the user
    user_input = input("You: ").strip()

    # Kill switch — user types quit to stop the agent
    if user_input.lower() in ["quit", "exit", "stop"]:
        print("\nAdvisor: Take care! Come back anytime you need help. 👋")
        break

    # Skip empty messages
    if not user_input:
        continue

    # Add user message to conversation history
    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    # Send full conversation to Groq and get response
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + conversation_history,
            max_tokens=1024
        )

        # Extract the reply text
        reply = response.choices[0].message.content

        # Add agent reply to history so it remembers next time
        conversation_history.append({
            "role": "assistant",
            "content": reply
        })

        print(f"\nAdvisor: {reply}\n")

    # If something goes wrong — tell the user clearly
    except Exception as e:
        print(f"\nAdvisor: Sorry, something went wrong. Please try again.")
        print(f"(Error: {e})\n")