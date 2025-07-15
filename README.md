# Cheshire Cat Gradio UI

A simple but powerful Gradio-based web interface to interact with a [Cheshire Cat AI](https://github.com/cheshire-cat-ai/core) instance.

This interface provides a clean, modern, ChatGPT-like experience, complete with user authentication and chat management features.

## Features

- **Token-Based Authentication**: Secure login system using username and password to obtain a bearer token.
- **Modern Chat Interface**: A responsive, message-based UI for conversations.
- **Full Chat Management**:
    - Create new chats.
    - Rename existing chats.
    - Delete chats.
    - Refresh the chat list.
- **Session Management**: A dedicated logout button to securely end the user session.
- **Easy Configuration**: All settings are managed through a `.env` file.
- **User-Friendly Feedback**: Clear warnings and info messages for all operations.

## Prerequisites

- Python 3.8+
- An running instance of the Cheshire Cat AI.

## Setup & Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/net7/simple-multi-chat-ui.git
    cd simple-multi-chat-ui
    ```

2.  **Create a Virtual Environment (Recommended)**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a file named `.env` in the root of the project directory and add the URL of your Cheshire Cat instance:

    ```env
    # .env
    BASE_URL="http://localhost:1865"
    ```
    Replace `http://localhost:1865` with the actual URL if your Cat is running elsewhere.

## Running the Application

Once the setup is complete, you can run the application with a single command:

```bash
python app.py
```

Alternatively, you can use Gradio's reload feature for development:

```bash
gradio app.py
```

The interface will be available at `http://127.0.0.1:7860`.

## How to Use

1.  **Login**: Open the web interface and enter the `username` and `password` configured in your Cheshire Cat instance to get an authentication token.
2.  **Manage Chats**: Use the sidebar on the left to create, rename, or delete chats. Click the refresh button to update the list.
3.  **Chat**: Select a chat from the list to view its history and start sending messages.
4.  **Logout**: Click the "Logout" button at the bottom of the sidebar to end your session and return to the login screen.

## Contributing

Contributions are welcome! If you have suggestions or want to improve the interface, feel free to open an issue or submit a pull request. 