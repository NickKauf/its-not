import os
import re
import time
import textwrap
from datetime import datetime

import anthropic
from escpos.printer import Network

# --- PRINTER CONFIG ---
PRINTER_IP = "192.168.1.245"
LINE_WIDTH = 42  # Characters per line on 80mm paper (Font A)
FONT_B_WIDTH = 56 # Characters per line on 80mm paper (Font B is smaller)
PRINT_PAUSE_SECONDS = 6.0 #Pause in seconds between prints
SYSTEM_PROMPT = """\
You are a generator for an art installation called "it's not."

You will be given a question about America. Your job is to generate a single completion to the phrase "it's not ___" that serves as a negative answer to the question.

Rules:
- Respond with ONLY the completion text — no "it's not" prefix, no quotes, no punctuation, no explanation
- Be specific, evocative, and visceral — not generic or abstract
- Draw from real political, social, cultural, economic realities
- Range across topics: immigration, incarceration, healthcare, housing, labor, surveillance, militarism, poverty, media, education, religion, environment, policing, etc.
- Vary sentence length and structure — some short and blunt, some longer and descriptive
- Never repeat a previous response (a list of prior responses will be provided)
- Think like a protest poet, not a pundit
- Go concrete: name the thing, the place, the body, the policy — not the abstraction
- Prefer the gut-level image over the intellectual observation\
"""

QUESTIONS = [
    "What is good for America?",
    "What is America?",
]

def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        print("API key loaded from environment.")
        return key
    key = input("Enter your Anthropic API key (paste it here): ").strip()
    if not key:
        print("No key provided. Exiting.")
        raise SystemExit(1)
    print("Key accepted.")
    return key

def show_menu():
    print()
    print("=" * 35)
    print("        it's not")
    print("=" * 35)
    print()
    print("Select a question:")
    print()
    for i, q in enumerate(QUESTIONS, 1):
        print(f"  {i}. {q}")
    print(f"  {len(QUESTIONS) + 1}. Enter your own question")
    print()

    while True:
        choices = "/".join(str(i) for i in range(1, len(QUESTIONS) + 2))
        choice = input(f"Choice ({choices}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(QUESTIONS) + 1:
            break
        print("Invalid choice, try again.")

    idx = int(choice)
    if idx <= len(QUESTIONS):
        return QUESTIONS[idx - 1]
    else:
        q = input("Enter your question: ").strip()
        if not q:
            print("No question entered, using default.")
            return QUESTIONS[0]
        return q

def select_mode():
    print()
    print("Mode:")
    print("  1. Manual (press Enter for each response)")
    print("  2. Auto (generate a specified batch of responses automatically)")
    print()
    while True:
        choice = input("Choice (1/2): ").strip()
        if choice in ("1", "2"):
            return "manual" if choice == "1" else "auto"
        print("Invalid choice, try again.")

def clean_response(text):
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    text = re.sub(r"^[Ii]t'?s\s+not\s+", "", text)
    text = text.rstrip(".")
    if text:
        text = text[0].lower() + text[1:]
    return text

def build_user_message(question, previous):
    parts = [f'Question: "{question}"']
    if previous:
        parts.append("")
        parts.append("Previous responses (do not repeat any of these):")
        for r in previous[-20:]: # Only send the last 20 to save context tokens
            parts.append(f"- {r}")
    parts.append("")
    parts.append("Generate the next response.")
    return "\n".join(parts)

def generate_one(client, question, previous):
    message = client.messages.create(
        model="claude-sonnet-4-20250514", # Restored to your specific model
        max_tokens=100,
        temperature=1.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(question, previous)}],
    )
    raw = message.content[0].text
    return clean_response(raw)

# --- PRINTER OUTPUT FUNCTION ---
def print_receipt(p, response, iteration_num):
    if not p:
        return
    
    try:
        # 1. HEADER (Everything left-aligned to bypass 112mm printer centering bug)
        p.set(align="left", font="a", bold=False, width=1, height=1)
        p.text("#" * LINE_WIDTH + "\n")
        
        p.set(align="left", font="a", bold=True, width=1, height=2)
        p.text("it's not".center(LINE_WIDTH) + "\n")
        
        p.set(align="left", font="a", bold=False, width=1, height=1)
        p.text("#" * LINE_WIDTH + "\n\n")

        # 2. BODY
        full_text = f"it's not {response}"
        wrapped = textwrap.fill(full_text, width=LINE_WIDTH)
        p.text(wrapped + "\n\n")

        # 3. FOOTER
        p.text("*" * LINE_WIDTH + "\n")

        iter_text = f"#{iteration_num}"
        p.text(iter_text.center(FONT_B_WIDTH) + "\n") ##add iteration number

        p.set(align="left", font="b", bold=False, width=1, height=1)
        timestamp = datetime.now().strftime("%b %d, %Y  %I:%M %p")
        p.text(timestamp.center(FONT_B_WIDTH) + "\n") ##add iteration timestamp
        
        p.set(align="left", font="a", bold=False, width=1, height=1)
        p.text("*" * LINE_WIDTH + "\n")

        # Feed to clear the tear bar/cutter
        p.text("\n" * 4)
    except Exception as e:
        print(f"\n[Printer Error during print: {e}]")

def generation_loop(client, question, printer):
    mode = select_mode()

    print(f'\nQuestion: "{question}"\n')
    
    iterations = 1
    if mode == "auto":
        while True:
            try:
                iterations = int(input("How many iterations would you like to print? (e.g., 10): ").strip())
                break
            except ValueError:
                print("Please enter a valid number.")
        print("-" * 35)
        print(f"Generating {iterations} responses automatically. Type Ctrl+C to stop.")
    else:
        print("-" * 35)
        print("Press ENTER to generate. Type 'q' to quit, 'b' to go back.")

    previous = []
    count = 0

    while (mode == "manual") or (mode == "auto" and count < iterations):
        if mode == "manual":
            cmd = input().strip().lower()
            if cmd == "q":
                print("Done.")
                raise SystemExit(0)
            if cmd == "b":
                return

        try:
            resp = generate_one(client, question, previous)
            if resp and resp not in previous:
                previous.append(resp)
                print(f"[{count+1}/{iterations if mode == 'auto' else '∞'}] it's not {resp}")
                
                # Send to physical printer
                print_receipt(printer, resp, count + 1)
                
                count += 1
                if mode == "auto" and count < iterations:
                    time.sleep(PRINT_PAUSE_SECONDS) # Prevent hitting API rate limits
            else:
                # Handle accidental duplicates
                if mode == "auto": 
                    continue

        except anthropic.APIError as e:
            print(f"[API error: {e}. Retrying...]")
            time.sleep(2)

    if mode == "auto":
        print(f"\n-- Finished printing {iterations} responses. --\n")

def main():
    print("\n" + "=" * 35)
    print("          it's not")
    print("=" * 35)

    # 1. Connect to API
    key = get_api_key()
    client = anthropic.Anthropic(api_key=key)

    # 2. Connect to Printer
    print("\nAttempting to connect to printer at", PRINTER_IP, "...")
    printer = None
    try:
        printer = Network(PRINTER_IP)
        print("Printer connected successfully!")
    except Exception as e:
        print(f"Warning: Could not connect to printer ({e}).")
        print("Script will run in terminal-only mode.")

    # 3. Main Loop
    while True:
        question = show_menu()
        generation_loop(client, question, printer)

if __name__ == "__main__":
    main()