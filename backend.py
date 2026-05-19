import os
import sqlite3 # NEW: Import SQLite
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional # NEW: For search query typing
from smolagents import ToolCallingAgent, LiteLLMModel
from app import get_my_files, tavily_search, get_weather_info, get_stock_price, currency_exchange_tool, get_dnd_info

app = FastAPI()

# --- NEW: DATABASE SETUP ---
DB_NAME = "chat_history.db"

def init_db():
    """Creates the history table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                response TEXT
            )
        ''')

init_db() # Run this when the server starts
# ---------------------------

# Setup Agent (Your existing setup)
os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_KEY_HERE"
os.environ["TAVILY_API_KEY"] = "YOUR_TAVILY_KEY_HERE"

model = LiteLLMModel(model_id="gpt-4o-mini", api_base="https://api.openai.com/v1")
agent = ToolCallingAgent(tools=[get_my_files, tavily_search, get_weather_info, get_stock_price, currency_exchange_tool, get_dnd_info], model=model, add_base_tools=False)

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        response = agent.run(request.prompt)
        response_text = str(response)

        # --- NEW: SAVE TO DB ---
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO history (prompt, response) VALUES (?, ?)", 
                         (request.prompt, response_text))
        # -----------------------

        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW: HISTORY & SEARCH ENDPOINT ---
@app.get("/history")
def get_history(q: Optional[str] = None):
    """
    Returns chat history. If 'q' is provided, it searches prompts and responses.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if q:
            # Search both the user prompt and the agent response
            search_term = f"%{q}%"
            cursor.execute("SELECT prompt, response FROM history WHERE prompt LIKE ? OR response LIKE ? ORDER BY id DESC", (search_term, search_term))
        else:
            # Return all history, newest first
            cursor.execute("SELECT prompt, response FROM history ORDER BY id DESC")
        
        rows = cursor.fetchall()
    
    # Convert list of tuples to list of dictionaries
    return [{"prompt": row[0], "response": row[1]} for row in rows]
# --------------------------------------
# To run this: uvicorn backend:app --reload --host 0.0.0.0 --port 8000