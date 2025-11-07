# client.py
import requests

SERVER_URL = "http://127.0.0.1:8000"

def send_message(sender: str, content: str):
    payload = {"sender": sender, "content": content}
    response = requests.post(f"{SERVER_URL}/send_message", json=payload)
    print(response.json())

def get_messages():
    response = requests.get(f"{SERVER_URL}/messages")
    print(response.json())

if __name__ == "__main__":
    send_message("Client1", "Hello, Server!")
    send_message("Client2", "Hey there 👋")
    get_messages()
