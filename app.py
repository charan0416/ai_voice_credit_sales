# -*- coding: utf-8 -*- # UTF-8 Encoding declaration
# app.py - Flask Backend for Butler Voice Bot (Fixes NameErrors)

import google.generativeai as genai
# Import the specific exception type needed
from google.api_core.exceptions import NotFound as GoogleApiNotFound # Renamed to avoid confusion

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
try:
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GOOGLE_API_KEY)
    logging.info("Gemini API Key loaded and configured successfully.")
except Exception as e:
    logging.error(f"FATAL ERROR: Could not configure Gemini API - {e}")
    logging.error("Please ensure the GEMINI_API_KEY environment variable is set correctly before running.")
    exit(1)

# --- System Prompt (Butler Persona - Enhanced Conversation - unchanged) ---
SYSTEM_PROMPT = """
You are "CardBot", a virtual assistant programmed in the manner of a traditional butler...
# ... (SYSTEM_PROMPT content remains the same as the previous "Enhanced Conversation" version) ...
I am programmed and ready to engage in a more thorough and helpful conversation, adhering strictly to these enhanced protocols.
"""

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app, resources={r"/interact": {"origins": "*"}})
logging.info("Flask app initialized with CORS enabled.")

# --- Conversation Management ---
conversation_history = {}
DEFAULT_SESSION_ID = "default_butler_session"

def initialize_chat():
    """Initializes a new Gemini chat session."""
    try:
        # Try the 'gemini-1.0-pro' model first
        # Inside initialize_chat()
        model_name = 'gemini-1.5-pro-latest'  # Try this model
        model = genai.GenerativeModel(model_name)
        logging.info(f"Attempting to use Gemini Model: '{model_name}'")
        # ... rest of the function ...
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [SYSTEM_PROMPT]},
            {'role': 'model', 'parts': ["Greetings. I am CardBot, a virtual assistant programmed by FutureBank. I am here to assist you in exploring our credit facilities. To begin, perhaps you could share what primarily motivates your interest in a new card today, or the types of benefits you value most?"]}
        ])
        logging.info(f"New chat session initialized successfully for Session ID: {DEFAULT_SESSION_ID}")
        return chat
    except Exception as e:
        logging.error(f"CRITICAL ERROR: Could not initialize Gemini chat model ('{model_name}') - {e}")
        return None

conversation_history[DEFAULT_SESSION_ID] = initialize_chat()
if conversation_history[DEFAULT_SESSION_ID] is None:
    logging.error("Exiting due to failure initializing the default chat session.")
    exit(1)

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def handle_root_get():
    """Provides a simple informational message at the root URL."""
    logging.info("GET request received for root '/'. Sending info page.")
    return """
    <html><head><title>CardBot Backend</title></head><body style='font-family: sans-serif; padding: 20px;'>
    <h1>CardBot Butler Backend</h1><p>This is the backend server. Access the application via the <strong>frontend HTML page</strong> (e.g., http://localhost:8080).</p>
    </body></html>""", 200

@app.route('/interact', methods=['POST'])
def interact_with_bot():
    """Handles conversation interaction POST requests from the frontend."""
    logging.debug(f"Received {request.method} request on /interact.")
    if not request.is_json:
        logging.warning("Invalid request: Not JSON.")
        return jsonify({"reply": "Error: Request must be JSON."}), 400

    data = request.get_json()
    user_text = data.get('text')

    # ** FIX: Define session_id BEFORE using it in logs **
    session_id = DEFAULT_SESSION_ID

    if not user_text:
        logging.warning("Invalid request: Missing 'text' field.")
        return jsonify({"reply": "Error: Missing 'text' in request body."}), 400

    # Now it's safe to log using session_id
    logging.info(f"Received text for session [{session_id}]: '{user_text}'")
    chat = conversation_history.get(session_id)
    if not chat:
        logging.error(f"CRITICAL: Chat object missing for session {session_id}!")
        return jsonify({"reply": "Apologies, a critical internal error occurred (session lost). Please restart the backend."}), 500

    # --- Interaction with Gemini API ---
    try:
        logging.debug(f"Sending message to Gemini ('gemini-1.0-pro') for session [{session_id}]...")
        print("DEBUG: Attempting to send message to Gemini...") # Keep this for now

        response = chat.send_message(user_text) # Attempt API call

        logging.debug(f"Received response object from Gemini for session [{session_id}].")

        # --- Safety/Block Handling ---
        if not response.parts:
            # ... (Code for blocked response remains the same) ...
            logging.warning(f"Session [{session_id}] - Gemini response potentially blocked or empty. Feedback: {response.prompt_feedback}")
            block_reason = getattr(response.prompt_feedback, 'block_reason', None)
            if block_reason:
                 bot_reply = "Pardon me, but I am unable to address that particular request due to established safety protocols."
                 logging.warning(f"Block Reason: {block_reason}")
            else:
                 bot_reply = "My apologies, the response seems to be empty or blocked for an unspecified reason."
            return jsonify({"reply": bot_reply}), 400
        else:
            # Extract text if response is valid
            bot_reply = response.text
            logging.info(f"Gemini Butler response for session [{session_id}]: '{bot_reply[:100]}...'")
            return jsonify({"reply": bot_reply}), 200 # OK

    # --- Specific Exception Handling ---
    # ** FIX: Use the imported exception name 'GoogleApiNotFound' **
    except GoogleApiNotFound as e:
         # Handle model not found specifically
         logging.error(f"API Error (NotFound): Model 'gemini-1.0-pro' likely not found or available. Error: {e}", exc_info=False)
         bot_reply = "My apologies, the specific AI model ('gemini-1.0-pro') needed appears to be unavailable with your current configuration. Please verify the model name, API key permissions, and project settings (like API and Billing enablement)."
         return jsonify({"reply": bot_reply}), 503 # Service Unavailable

    except Exception as e:
        # Catch ALL other potential errors during the API call or response processing
        print(f"!!!!!! BACKEND EXCEPTION CAUGHT !!!!!!\n{type(e).__name__}: {e}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # Keep debug print
        logging.error(f"Error during Gemini API call or processing for session [{session_id}]: {e}", exc_info=True) # Log full traceback
        bot_reply = "My apologies, a technical difficulty prevents me from responding fully at this moment. Please try again shortly."
        return jsonify({"reply": bot_reply}), 500 # Internal Server Error


# --- Run the Flask App ---
if __name__ == '__main__':
    print("-----------------------------------------------------")
    print("Starting Flask backend server for Butler Voice Bot...")
    print("Ensure the GEMINI_API_KEY environment variable is set.")
    port_to_run = 8000 # Ensure this matches frontend BACKEND_URL
    print(f"Backend running on: http://localhost:{port_to_run}")
    print("Access the application via the frontend HTML page (likely http://localhost:8080)")
    print("Use CTRL+C to stop the server.")
    print("-----------------------------------------------------")
    app.run(host='0.0.0.0', port=port_to_run, debug=False)