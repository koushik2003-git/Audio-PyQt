import os
import json
import re
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# === OpenAI Setup ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def evaluate_objectives(objectives: dict, partial_summary: str, threshold: float = 1.0):
    """
    Evaluate objectives vs partial summary using OpenAI embeddings (no torch needed).
    Also lists out speakers who haven't spoken yet.
    """

    # --- Extract speakers from summary ---
    spoken_speakers = sorted(set(re.findall(r"Speaker[_\s]*(\d+)", partial_summary)))
    spoken_speakers = [f"Speaker_{s}" for s in spoken_speakers]
    all_speakers = sorted(set(re.findall(r"Speaker[_\s]*\d+", partial_summary)))
    if not all_speakers:
        all_speakers = [f"Speaker_{i}" for i in range(1, 6)]
    silent_speakers = [s for s in all_speakers if s not in spoken_speakers]

    # --- Get embeddings ---
    texts = list(objectives.values()) + [partial_summary]
    response = openai_client.embeddings.create(model="text-embedding-3-large", input=texts)
    embeddings = [np.array(e.embedding) for e in response.data]
    summary_emb = embeddings[-1]

    # --- Evaluate each objective ---
    results = {}
    for obj, desc, emb in zip(objectives.keys(), objectives.values(), embeddings[:-1]):
        score = cosine_similarity(emb, summary_emb)
        score = float((score + 1) / 2)  # normalize [-1, 1] → [0, 1]
        if score > 0.85:
            label = "Highly Relevant"
        elif score > 0.6:
            label = "Relevant"
        elif score > 0.4:
            label = "Somewhat Related"
        else:
            label = "Irrelevant"

        results[obj] = {"score": round(score, 2), "label": label}

    results["user"] = silent_speakers
    return results
