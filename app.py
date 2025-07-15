import gradio as gr
import requests
import json
import logging
import os
import time
from dotenv import load_dotenv

# --- Pre-run Setup ---

# Load environment variables from .env file
load_dotenv()

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---

# The base URL of the Cheshire Cat API. Should be set in the .env file.
# Example: BASE_URL="http://localhost:1865"
BASE_URL = os.getenv("BASE_URL", "http://localhost:1865")

# API endpoint paths for better organization
API_ENDPOINTS = {
    "token": "/auth/token",
    "get_chats": "/memory/collections/chat/points/by_metadata_chat",
    "create_chat": "/createChat",
    "delete_chat": "/delete_chat",
    "rename_chat": "/memory/collections/points/changeNameChat",
    "get_messages": "/giveAll",
    "send_message": "/message"
}


# --- Logging & Error Handling ---

def log_and_warn(message):
    """Logs a warning and displays it in the Gradio interface."""
    logging.warning(message)
    gr.Warning(message)

def log_and_info(message):
    """Logs an info message and displays it in the Gradio interface."""
    logging.info(message)
    gr.Info(message)

def log_and_success(message):
    """Logs an info message and displays a success message in the Gradio interface."""
    logging.info(message)
    gr.Success(message)

def handle_api_error(e, context="API call"):
    """Logs a detailed error from a requests exception for better debugging."""
    error_message = f"Error in {context}: {e}"
    if hasattr(e, 'response') and e.response is not None:
        try:
            error_body = e.response.json()
            error_message += f" | Details: {json.dumps(error_body, indent=2)}"
        except json.JSONDecodeError:
            error_message += f" | Details: {e.response.text}"
    log_and_warn(error_message)


# --- API Client ---

def get_headers(auth_token):
    """Constructs the authorization headers for API requests."""
    if not auth_token:
        raise ValueError("Authentication token is missing.")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

def get_chats(auth_token):
    """Fetches all non-deleted chats for the authenticated user."""
    try:
        headers = get_headers(auth_token)
        response = requests.post(f"{BASE_URL}{API_ENDPOINTS['get_chats']}", headers=headers)
        response.raise_for_status()
        data = response.json()
        if "points" in data and data["points"]:
            return [[p["metadata"].get("name", "Unnamed Chat"), p["id"]] for p in data["points"]]
        return []
    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "fetching chats")
        return []

def create_chat(auth_token, chat_name):
    """Creates a new chat with the given name."""
    try:
        headers = get_headers(auth_token)
        payload = {"metadata": {"name": chat_name, "content": chat_name}}
        response = requests.post(f"{BASE_URL}{API_ENDPOINTS['create_chat']}", headers=headers, json=payload)
        response.raise_for_status()
        log_and_success(f"Chat '{chat_name}' created successfully!")
    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "creating chat")

def delete_chat(auth_token, chat_id):
    """Deletes a specific chat by its ID."""
    if not chat_id:
        log_and_warn("Please select a chat to delete.")
        return
    try:
        headers = get_headers(auth_token)
        params = {"chat_id": chat_id}
        response = requests.delete(f"{BASE_URL}{API_ENDPOINTS['delete_chat']}", headers=headers, params=params)
        response.raise_for_status()
    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "deleting chat")

def rename_chat(auth_token, chat_id, new_name):
    """Renames a specific chat by its ID."""
    if not chat_id:
        log_and_warn("Please select a chat to rename.")
        return
    if not new_name.strip():
        log_and_warn("New name cannot be empty.")
        return
        
    try:
        headers = get_headers(auth_token)
        params = {"chat_id": chat_id, "name": new_name}
        response = requests.post(f"{BASE_URL}{API_ENDPOINTS['rename_chat']}", headers=headers, params=params)
        response.raise_for_status()
        log_and_success(f"Chat {chat_id} renamed to '{new_name}'.")
    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "renaming chat")

def get_chat_messages(auth_token, chat_id):
    """Fetches all messages for a given chat ID."""
    if not chat_id:
        return [], "Select a chat to see messages"
    try:
        headers = get_headers(auth_token)
        params = {"chat_id": chat_id}
        response = requests.post(f"{BASE_URL}{API_ENDPOINTS['get_messages']}", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        chat_name = data.get("Name", "Current Chat")
        messages = data.get("Messages", {}).get("points", [])
        
        history = []
        for msg in messages:
            meta = msg.get("metadata", {})
            # Display user and bot messages in order
            if meta.get("text"):
                history.append({"role": "user", "content": meta["text"]})
            if meta.get("bot"):
                history.append({"role": "assistant", "content": meta["bot"]})

        return history, f"History for: {chat_name}"
    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "fetching messages")
        return [], "Error loading messages"
    except (KeyError, TypeError) as e:
        log_and_warn(f"Error parsing response: {e}")
        return [], "Could not parse message response"

def send_message_and_get_reply(auth_token, chat_id, text):
    """Sends a message to the cat and gets the full chat history back."""
    if not chat_id:
        log_and_warn("Cannot send message: no chat selected.")
        return None
    if not text.strip():
        log_and_warn("Cannot send an empty message.")
        return None

    try:
        headers = get_headers(auth_token)
        payload = {"text": text, "chat_id": chat_id}
        send_response = requests.post(
            f"{BASE_URL}{API_ENDPOINTS['send_message']}",
            headers=headers,
            json=payload,
            stream=False
        )
        send_response.raise_for_status()

        # NOTE: This delay is a workaround for eventual consistency in the backend.
        # The Cheshire Cat API processes messages asynchronously. After sending a
        # message, it may take a moment for the new message to be reflected in the
        # chat history. This sleep provides a buffer to increase the chances that
        # the subsequent 'get_chat_messages' call retrieves the updated history.
        # In a production system, a more robust solution like WebSockets or
        # server-sent events would be preferable for real-time updates.
        time.sleep(1) 
        
        updated_history, _ = get_chat_messages(auth_token, chat_id)
        
        return updated_history

    except (requests.exceptions.RequestException, ValueError) as e:
        handle_api_error(e, "sending message")
        return None
    
# --- Gradio UI ---

with gr.Blocks(theme=gr.themes.Soft(), title="Simple Multi Chat UI for Cheshire Cat") as demo:
    
    # State variables to hold session data
    auth_token_state = gr.State(None)
    chat_list_data_state = gr.State([])
    selected_chat_id_state = gr.State(None) 

    gr.Markdown("# 🐈 Simple Multi Chat UI for Cheshire Cat")
    
    # Login View: Initially visible
    with gr.Group(visible=True) as login_view:
        gr.Markdown("## Login")
        username_input = gr.Textbox(label="Username", placeholder="Enter your username")
        password_input = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
        login_btn = gr.Button("Login", variant="primary")

    # Main Chat View: Initially hidden
    with gr.Group(visible=False) as main_view:
        with gr.Row(equal_height=False):
            # Left Column: Chat management
            with gr.Column(scale=1, min_width=250):
                gr.Markdown("### 💬 Chats")
                
                with gr.Accordion("➕ Create New Chat", open=True):
                    new_chat_name_input = gr.Textbox(label="New Chat Name", placeholder="e.g., 'My Holiday Plans'")
                    create_chat_btn = gr.Button("Create Chat", variant="primary")
                
                chat_selector_radio = gr.Radio(label="Select a Chat", interactive=True)
                refresh_chats_btn = gr.Button("🔄 Refresh List")

                with gr.Accordion("✏️ Manage Current Chat", open=False):
                    rename_chat_name_input = gr.Textbox(label="Set New Name")
                    rename_chat_btn = gr.Button("Rename Chat")
                    delete_chat_btn = gr.Button("🗑️ Delete Chat", variant="stop")

                logout_btn = gr.Button("Logout")

            # Right Column: Chatbot interface
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Chat History", height=600, type="messages")
                
                with gr.Row():
                    message_input = gr.Textbox(
                        label="Send a message", 
                        placeholder="Type here...", 
                        scale=4, 
                        interactive=True, 
                        container=False
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")

# --- UI Logic & Event Handlers ---

    # Centralized function to refresh chat list and update UI components
    def refresh_and_update_components(auth_token):
        """Fetches all chats and updates the selector with (name, id) choices."""
        if not auth_token:
            return gr.update(choices=[]), []
            
        chats = get_chats(auth_token)
        return gr.update(choices=chats, value=None), chats

    def login(username, password):
        """Handles user authentication, fetches the token, and switches to the main view."""
        if not username or not password:
            gr.Warning("Username and Password are required.")
            return gr.update(visible=True), gr.update(visible=False), None, [], gr.update(choices=[])
        
        try:
            response = requests.post(
                f"{BASE_URL}{API_ENDPOINTS['token']}",
                headers={"Content-Type": "application/json"},
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            
            token_data = response.json()
            auth_token = token_data.get("access_token")

            if not auth_token:
                gr.Warning("Login failed: No token received.")
                return gr.update(visible=True), gr.update(visible=False), None, [], gr.update(choices=[])

            log_and_success("Login successful.")
            
            chat_choices, chat_list = refresh_and_update_components(auth_token)
        
            return gr.update(visible=False), gr.update(visible=True), auth_token, chat_list, chat_choices
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                gr.Warning("Invalid username or password.")
            else:
                handle_api_error(e, "authentication")
            return gr.update(visible=True), gr.update(visible=False), None, [], gr.update(choices=[])
        except requests.exceptions.RequestException as e:
            handle_api_error(e, "authentication")
            return gr.update(visible=True), gr.update(visible=False), None, [], gr.update(choices=[])

    def logout():
        """Logs the user out, clears all states, and returns to the login screen."""
        log_and_info("User logged out.")
        return (
            gr.update(visible=True),      # Show login view
            gr.update(visible=False),     # Hide main view
            None,                         # Clear auth token
            [],                           # Clear chat list data
            None,                         # Clear selected chat ID
            [],                           # Clear chatbot history
            gr.update(choices=[], value=None), # Reset chat selector
            "",                           # Clear username input
            ""                            # Clear password input
        )

    def get_name_from_id(selected_id, chat_list):
        """Helper to find a chat's name from its unique ID in the state."""
        return next((name for name, chat_id in chat_list if chat_id == selected_id), None)

    def on_chat_select(selected_id, auth_token):
        """Handles chat selection: fetches and displays its message history."""
        if selected_id:
            history, _ = get_chat_messages(auth_token, selected_id)
            return history, selected_id
        return [], None

    def handle_create_chat(name, auth_token):
        """Creates a new chat and refreshes the chat list."""
        create_chat(auth_token, name)
        updated_choices, updated_list = refresh_and_update_components(auth_token)
        return updated_choices, updated_list, "" # Clear input field

    def handle_delete_chat(selected_id, chat_list_data, auth_token):
        """Deletes the selected chat and refreshes the list."""
        if selected_id:
            chat_name = get_name_from_id(selected_id, chat_list_data) or selected_id
            delete_chat(auth_token, selected_id)
            log_and_success(f"Chat '{chat_name}' deleted.")
            updated_choices, updated_list = refresh_and_update_components(auth_token)
            return updated_choices, updated_list, None, [] # Reset selector and history
        else:
            log_and_warn("No chat selected to delete.")
            return gr.update(), gr.update(), gr.update(), gr.update()
            
    def handle_rename_chat(selected_id, new_name, auth_token):
        """Renames the selected chat and refreshes the list."""
        if not selected_id:
            gr.Warning("Please select a chat to rename.")
            return gr.update(), gr.update(), new_name

        rename_chat(auth_token, selected_id, new_name)
        refreshed_choices, refreshed_list = refresh_and_update_components(auth_token)
        return refreshed_choices, refreshed_list, "" # Clear input

    def handle_send_and_refresh(selected_chat_id, text, auth_token):
        """Sends a message, then refreshes and displays the updated chat history."""
        if not selected_chat_id:
            log_and_warn("Please select a chat first.")
            return [], ""
            
        updated_history = send_message_and_get_reply(auth_token, selected_chat_id, text)
        
        # If the API call failed, updated_history will be None. Keep the old history.
        if updated_history is None:
            # To avoid losing the current view, we just return the current history
            # A better approach could be to return gr.update() to not change the component
            current_history, _ = get_chat_messages(auth_token, selected_chat_id)
            return current_history, text # Return original text to not clear input

        return updated_history, "" # Clear input on success
        
# --- Event Handler Wiring ---

    login_btn.click(
        fn=login,
        inputs=[username_input, password_input],
        outputs=[login_view, main_view, auth_token_state, chat_list_data_state, chat_selector_radio]
    )

    logout_btn.click(
        fn=logout,
        outputs=[
            login_view, main_view, auth_token_state, chat_list_data_state, 
            selected_chat_id_state, chatbot, chat_selector_radio, 
            username_input, password_input
        ]
    )

    refresh_chats_btn.click(
        fn=refresh_and_update_components,
        inputs=[auth_token_state],
        outputs=[chat_selector_radio, chat_list_data_state]
    )

    chat_selector_radio.change(
        fn=on_chat_select,
        inputs=[chat_selector_radio, auth_token_state],
        outputs=[chatbot, selected_chat_id_state]
    )
    
    create_chat_btn.click(
        fn=handle_create_chat,
        inputs=[new_chat_name_input, auth_token_state],
        outputs=[chat_selector_radio, chat_list_data_state, new_chat_name_input]
    )

    delete_chat_btn.click(
        fn=handle_delete_chat,
        inputs=[selected_chat_id_state, chat_list_data_state, auth_token_state],
        outputs=[chat_selector_radio, chat_list_data_state, selected_chat_id_state, chatbot]
    )

    rename_chat_btn.click(
        fn=handle_rename_chat,
        inputs=[selected_chat_id_state, rename_chat_name_input, auth_token_state],
        outputs=[chat_selector_radio, chat_list_data_state, rename_chat_name_input]
    )

    # Trigger message sending on button click or Enter key press
    send_btn.click(
        fn=handle_send_and_refresh,
        inputs=[selected_chat_id_state, message_input, auth_token_state],
        outputs=[chatbot, message_input]
    )
    message_input.submit(
        fn=handle_send_and_refresh,
        inputs=[selected_chat_id_state, message_input, auth_token_state],
        outputs=[chatbot, message_input]
    )

if __name__ == "__main__":
    demo.launch() 