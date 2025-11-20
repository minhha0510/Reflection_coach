import os
import json
import requests
from datetime import datetime, timedelta
#from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

# --- CONFIGURATION ---

# 1. SET YOUR DEEPSEEK API KEY

#load_dotenv() 

DEEPSEEK_API_KEY = "NA_For_now"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# --- PROMPTS ---

DAILY_GUIDANCE_PROMPT = """
You are a highly skilled performance coach and psychoanalyst specializing in Kolb's Learning Cycle.
Your goal is to guide the user through a reflective process.

You will receive:
1.  A user's initial, unstructured thought.
2.  A JSON template of Kolb's Learning Cycle to use as your framework.

Your task is to:
1.  Read the user's thought and silently map it to the Kolb's template to see where they are in the cycle (e.g., Are they describing a 'Concrete Experience'?).
2.  Ask them 1-2 concise, guiding questions to help them move to the *next* step of the cycle (e.g., from 'Concrete Experience' to 'Reflective Observation').
3.  Be conversational, empathetic, and curious. Ask your follow-up questions in friendly, open-ended language.
4.  Continue the conversation, guiding them through the cycle ('Observation' -> 'Abstract Conceptualization' -> 'Active Experimentation') based on their answers.

Example:
- If user describes an event, ask what they *felt* or *noticed* (Reflective Observation).
- If they describe feelings, ask them *why* they think it happened or what patterns they see (Abstract Conceptualization).
- If they identify a pattern, ask what they could *do* differently next time (Active Experimentation).
"""

# This prompt is now used for FINAL summarization
DAILY_SYSTEM_PROMPT = """
You are a psychoanalyst and high-performance coach. The user is providing a FULL conversation from a guided reflection session.
Your task is to analyze the *entire* conversation and synthesize it into a final structured summary.
You MUST output ONLY a JSON object (no other text) with the following exact schema:

{
  "summary": "A concise, one-sentence summary of the event and final outcome/insight.",
  "trigger_cues": "What was the specific physical (body cue) or environmental trigger that started the feeling? (e.g., 'Opened laptop for class', 'Felt a knot in stomach').",
  "emotional_response": "The primary feeling that arose *before* the action (e.g., 'Overwhelm', 'Anxiety', 'Frustration').",
  "cognitive_pattern": "What was the core thought process or story the user identified? (e.g., 'This is too big to finish', 'I might fail', 'I need to be perfect').",
  "behavioral_action": "What action did this sequence originally lead to? (e.g., 'Procrastination', 'Avoidance').",
  "proposed_solution": "The user's *final* proposed solution or experiment from the 'Active Experimentation' phase (e.g., 'Next time, I will try a 5-minute timer').",
  "key_takeaway": "The main lesson or insight the user learned from the *entire* reflection."
}
"""

WEEKLY_SYSTEM_PROMPT = """
You are a thoughtful and curious performance coach, trained in psychoanalysis. The user is reviewing their reflections from the past week, which will be provided as context.
Your goal is to help them identify recurring themes, habits, and pitfalls by asking TWO insightful, connected, open-ended questions at a time.

DO:
- Act as a performance coach. Your tone is curious, empathetic, and analytical.
- Focus on identifying the *connection* between cues, feelings, thoughts, and actions (e.g., "I see this feeling of 'overwhelm' often follows a trigger of 'opening your laptop'. What story does your mind tell you in that exact moment?").
- Ask the user to explore the *consequences* of these patterns (e.g., "When that thought pattern appears, what does it usually lead to? And how does that outcome make you feel?").
- Probe for underlying assumptions or beliefs (e.g., "You mentioned 'needing to be perfect' on two days. What do you think is the root of that pressure? And how does it serve or hinder you?").
- Help the user analyze *why* a pattern arises and guide them to think about ways to overcome or prevent it.
- Ask exactly two questions per response, with the second question building on the first.
"""

# --- CORE FUNCTIONS ---

def call_llm(system_prompt, user_prompt, history=None):
    """
    Handles the API call to the LLM with improved error handling.
    'history' is a list of previous chat messages, e.g.:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        return "Error: API_KEY not set."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    # Construct the message history
    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        messages.extend(history)
        
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": "deepseek-chat", # Or whatever model you are using
        "messages": messages
        # Add other parameters like 'temperature' if needed
    }

    print(f"\n--- Sending request to {DEEPSEEK_API_URL} ---")
    # print(f"Payload: {json.dumps(payload, indent=2)}") # Uncomment this line for deep debugging

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        
        print(f"--- Response Received ---")
        print(f"Status Code: {response.status_code}")
        # print(f"Response Body: {response.text}") # Uncomment this line for deep debugging

        # Check for HTTP errors
        response.raise_for_status() # This will raise an exception for 4xx or 5xx status codes
        
        # Try to parse the JSON response
        try:
            data = response.json()
            
            # Extract the content, checking for structure
            try:
                content = data['choices'][0]['message']['content']
                return content
            except (KeyError, IndexError, TypeError) as e:
                print(f"Error: Could not parse expected data from LLM response. Error: {e}")
                print(f"Full data: {data}")
                return "Error: Unexpected data structure in API response."

        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON response. Error: {e}")
            return f"Error: Failed to decode JSON. Response text was: {response.text}"
        
    except requests.exceptions.Timeout:
        print("Error: API call timed out.")
        return "Error: The request timed out."
    except requests.exceptions.RequestException as e:
        # This catches network errors, DNS errors, and HTTP error statuses from raise_for_status()
        print(f"Error: API call failed with an exception: {e}")
        return f"Error: API call failed: {e}"


def save_reflection(entry_data, raw_text, daily_dir):
    """Saves the structured reflection to the daily folder."""
    if not os.path.exists(daily_dir):
        os.makedirs(daily_dir)

    today = datetime.now()
    # MODIFICATION: Changed filename to include timestamp to allow multiple entries per day
    filename = os.path.join(daily_dir, f"{today.strftime('%Y-%m-%d-%H%M%S')}.md")
    
    # Use the new, more detailed schema
    content = f"""---
date: {today.isoformat()}
summary: {entry_data.get('summary', 'N/A')}
trigger_cues: {entry_data.get('trigger_cues', 'N/A')}
emotional_response: {entry_data.get('emotional_response', 'N/A')}
cognitive_pattern: {entry_data.get('cognitive_pattern', 'N/A')}
behavioral_action: {entry_data.get('behavioral_action', 'N/A')}
solution: {entry_data.get('proposed_solution', 'N/A')}
takeaway: {entry_data.get('key_takeaway', 'N/A')}
---

# Daily Reflection: {today.strftime('%Y-%m-%d %H:%M:%S')}

## Raw Thoughts
{raw_text}
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"\nSuccessfully saved reflection to {filename}")
    print(f"Summary: {entry_data.get('summary')}")
    
# Function to load Kolb's template from a JSON file
def load_kolb_template():
    """Loads the Kolb's cycle template from a JSON file."""
    # Assumes the template is in the same directory as the script
    # Uses __file__ to get the script's directory, making it more robust
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'Kolb_template.json')

    print(f"Loading Kolb template from: {template_path}")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        return template
    except FileNotFoundError:
        print(f"Error: 'Kolb_template.json' not found in script directory.")
        print("Please make sure the file exists and is named correctly.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse 'Kolb_template.json'.")
        print(f"Please check for syntax errors in the JSON file. Details: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading the template: {e}")
        return None

# --- MODES ---

def daily_reflection(daily_dir):
    """
    Mode 1: Capture and process a daily reflection using a guided
    Kolb's cycle conversation.
    MODIFIED: This is now an interactive loop.
    """
    print("--- Daily Reflection ---")
    
    # 1. Load Kolb's Template
    kolb_template = load_kolb_template()
    if kolb_template is None:
        # Error messages are handled inside the load function
        return
        
    # 2. Get initial unstructured thought
    print("\nEnter your unstructured thoughts. Type 'done' (on its own line) to finish.")
    raw_text = []
    while True:
        line = input()
        if line.lower().strip() == 'done':
            break
        raw_text.append(line)
        
    if not raw_text:
        print("No input received. Exiting.")
        return
        
    initial_raw_thoughts = "\n".join(raw_text)
    
    print("\nStarting guided reflection... (Type 'save' at any time to finish and save)")
    
    # 3. Start the conversational loop
    chat_history = []
    
    # Prepare the very first prompt for the guidance LLM
    template_str = json.dumps(kolb_template, indent=2)
    user_message = (
        f"Here is my unstructured thought:\n{initial_raw_thoughts}\n\n"
        f"Here is the Kolb's Cycle template we should use to guide the reflection:\n{template_str}\n\n"
        "Please analyze my thought, map it to the cycle, and ask me 1-2 questions to help me dig deeper."
    )

    while True:
        # Call the guidance LLM
        llm_response = call_llm(DAILY_GUIDANCE_PROMPT, user_message, chat_history)
        
        if llm_response.startswith("Error:"):
            print(f"\nLLM call failed: {llm_response}")
            print("Aborting reflection.")
            return

        print(f"\nCoach: {llm_response}")
        
        # Add to history
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": llm_response})
        
        # Get user's next message
        user_input = input("You: ")
        
        if user_input.lower().strip() == 'save':
            print("\nSaving your reflection...")
            break
        
        user_message = user_input # This will be the prompt for the next loop

    # 4. Final Summarization and Save
    # We build a single string of the *entire* conversation for the final summary prompt
    
    # Start with the initial thoughts, clearly labeled
    full_conversation_text = f"Initial Thoughts:\n{initial_raw_thoughts}\n\n"
    
    # Add the rest of the chat
    # We skip the first "user" message in history, as it was the giant prompt
    # and we've already added the 'initial_raw_thoughts'
    for i in range(len(chat_history)):
        message = chat_history[i]
        if message["role"] == "assistant":
            full_conversation_text += f"Coach: {message['content']}\n\n"
        elif i > 0: # Skip the first giant user prompt
            full_conversation_text += f"You: {message['content']}\n\n"

    print("\nProcessing final summary with LLM...")
    
    # Use the ORIGINAL system prompt to summarize the WHOLE conversation
    llm_response = call_llm(DAILY_SYSTEM_PROMPT, full_conversation_text)
    
    if llm_response.startswith("Error:"):
        print(f"\nLLM summarization failed. The reflection was NOT saved.")
        print(f"Details: {llm_response}")
        return

    try:
        entry_data = json.loads(llm_response)
        # Save the full conversation text, not just the raw thoughts
        save_reflection(entry_data, full_conversation_text, daily_dir)
    except json.JSONDecodeError:
        print(f"Error: Summarizing LLM did not return valid JSON. The reflection was NOT saved.")
        print(f"Response was:\n{llm_response}")


def load_weekly_entries(daily_dir):
    """Loads all reflection files from the past 7 days from the daily folder."""
    print("Loading reflections from the past 7 days...")
    all_entries = []
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    if not os.path.exists(daily_dir):
        return "No daily reflection directory found. Please add some daily reflections first."

    for filename in sorted(os.listdir(daily_dir)):
        if not filename.endswith(".md"):
            continue
            
        try:
            # This logic remains correct, as it only checks the first 10 characters (the date)
            file_date = datetime.strptime(filename[:10], '%Y-%m-%d')
            if file_date >= seven_days_ago:
                filepath = os.path.join(daily_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    all_entries.append(f"--- Entry from {filename} ---\n{f.read()}\n")
        except ValueError:
            continue # Skip files that don't match date format

    if not all_entries:
        return "No reflections found from the past 7 days."
        
    return "\n".join(all_entries)

def save_weekly_review(chat_history, context, weekly_dir):
    """Saves the full weekly review conversation to a file."""
    if not os.path.exists(weekly_dir):
        os.makedirs(weekly_dir)
    
    today = datetime.now()
    filename = os.path.join(weekly_dir, f"Weekly-Review-{today.strftime('%Y-%m-%d')}.md")
    
    content = f"# Weekly Review: {today.strftime('%Y-%m-%d')}\n\n"
    content += "## Daily Entries Loaded for This Review\n"
    content += "```\n"
    content += context
    content += "\n```\n\n"
    content += "## Reflection Conversation\n\n"
    
    # Format the chat history
    # Add the initial user prompt (which isn't in history)
    content += f"**You:** Here are my reflections from the past week. Please help me dig deeper.\n\n"
    for message in chat_history:
        if message["role"] == "user":
            content += f"**You:** {message['content']}\n\n"
        elif message["role"] == "assistant":
            content += f"**Coach:** {message['content']}\n\n"
            
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nSuccessfully saved weekly review to {filename}")
    except OSError as e:
        print(f"Error saving weekly review: {e}")

def weekly_review(daily_dir, weekly_dir):
    """Mode 2: Start a conversational weekly review."""
    print("--- Weekly Review ---")
    
    # Load context from daily directory
    context = load_weekly_entries(daily_dir)
    print(context)
    
    if "No reflections" in context:
        return

    # Start the conversation
    chat_history = []
    user_message = "Here are my reflections from the past week. Please help me dig deeper."

    while True:
        # Combine the fixed context (weekly entries) with the dynamic chat history
        # We send the full context + history each time
        prompt_with_context = f"Here is the context of my weekly entries:\n{context}\n\nNow, let's continue our conversation.\nUser: {user_message}"
        
        llm_response = call_llm(WEEKLY_SYSTEM_PROMPT, prompt_with_context, chat_history)
        
        # Check for errors from the LLM call
        if llm_response.startswith("Error:"):
            print(f"\nLLM call failed: {llm_response}")
            print("Exiting weekly review.")
            break
            
        print(f"\nCoach: {llm_response}")
        
        # Add to history *only after successful call*
        if user_message != "Here are my reflections from the past week. Please help me dig deeper.":
            chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": llm_response})
        
        # Get user's next message
        user_message = input("You: ")
        
        if user_message.lower().strip() in ['quit', 'exit', 'q']:
            print("Saving your weekly reflection...")
            save_weekly_review(chat_history, context, weekly_dir)
            print("Great reflection session. See you next week!")
            break

# --- MAIN EXECUTION ---

def main():
    print("--- Cognitive Habit Reflector ---")
    
# AUTO-DETECT PATH: Gets the folder where THIS script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    daily_dir = os.path.join(script_dir, "daily")
    weekly_dir = os.path.join(script_dir, "weekly")

    print(f"Storage Path: {script_dir}")

    print(f"Using daily directory: {daily_dir}")
    print(f"Using weekly directory: {weekly_dir}")

    # Loop for continuous use
    while True:
        print("\n--- Main Menu ---")
        print("1: Daily Reflection")
        print("2: Weekly Review")
        print("3: Exit")
        choice = input("Choose mode (1, 2, or 3): ")
        
        if choice == '1':
            daily_reflection(daily_dir)
        elif choice == '2':
            weekly_review(daily_dir, weekly_dir)
        elif choice == '3':
            print("Exiting.")
            break # Break the while loop
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()