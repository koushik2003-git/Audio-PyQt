# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Message Exchange Server")

class Message(BaseModel):
    sender: str
    content: str

messages: List[Message] = []

@app.post("/send_message")
async def send_message(msg: Message):
    messages.append(msg)
    return {"status": "Message received", "total_messages": len(messages)}

@app.get("/messages")
async def get_messages():
    return {"messages": messages}
