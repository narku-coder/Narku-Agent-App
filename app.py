import os
import requests
from flask import Flask, render_template, request, jsonify
from smolagents import ToolCallingAgent, LiteLLMModel, tool 

app = Flask(__name__)

# --- CONFIGURATION & API KEYS ---
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
STOCK_API_KEY = os.getenv("STOCK_API_KEY")  
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# --- TOOLS DEFINITION ---
@tool
def get_my_files(filename: str, search_path: str = "/") -> str:
    """
    Searches the local drive for a file and reads its contents.

    Args:
        filename: The name of the file to search for.
        search_path: The directory to start the search from (defaults to root).

    Returns:
        str: The contents of the file if found, or an error message.
    """
    found_path = None
    
    # Safety: Limit search to current directory for this demo if path is root
    # (Scanning the whole C:/ drive can be slow and cause permission errors)
    search_root = "." if search_path == "/" else search_path
    
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            found_path = os.path.join(root, filename)
            break 

    if found_path:
        try:
            with open(found_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error: Could not read file at {found_path}. {e}"
    
    return f"Error: The file '{filename}' was not found in {search_path}."

@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Perform a web search
    Args:
        query: The search query
        max_results: The maximum number of results to return
    Returns:
        str: The search result
    """
    url = "https://api.tavily.com/search"
    headers = {"Authorization": f"Bearer {TAVILY_API_KEY}"}
    payload = {"query": query, "num_results": max_results}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return str(response.json())
    except Exception as e:
        return f"Error performing search: {e}"

@tool
def get_weather_info(city: str) -> str:
    """Retrieve the current weather information for a given city.
    Args:
        city: The name of the city to get the weather information for.
    Returns:
        str: A description of the current weather and temperature in the city.
    """
    api_key = "35fb9b66355042c654d8b3d3ceb18eba"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return f"The weather in {city} is {data['weather'][0]['description']} with a temperature of {data['main']['temp']}°C."
        else:
            return f"Could not retrieve weather information for {city}."
    except Exception as e:
        return f"Error getting weather: {e}"
    
@tool
def get_stock_price(symbol:str) -> str:
    """Retrieve the current stock price for a given stock symbol.
    Args:
        symbol: The symbol for the stock
    Returns:
        str: A string containing the price for the specified stock.
    """

    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={STOCK_API_KEY}"

    response = requests.get(url)
    data = response.json()    
    return (f"Current Price of {symbol}: {data['c']}")

@tool
def currency_exchange_tool(source_currency: str, target_currency: str, amount: float = 1.0) -> str:
    """
    Converts an amount from one currency to another using current exchange rates.

    Args:
        source_currency: The three-letter code of the currency to convert from (e.g., 'USD').
        target_currency: The three-letter code of the currency to convert to (e.g., 'EUR').
        amount: The amount of money to convert (defaults to 1.0).

    Returns:
        str: A string showing the conversion result or an error message.
    """
    # specific API endpoint allows changing the base currency
    url = f"https://api.exchangerate-api.com/v4/latest/{source_currency.upper()}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raises error for bad HTTP codes (404, 500)
        data = response.json()
        
        target = target_currency.upper()
        
        if "rates" in data and target in data["rates"]:
            rate = data["rates"][target]
            converted_amount = amount * rate
            return f"{amount} {source_currency.upper()} = {converted_amount:.2f} {target} (Rate: {rate})"
        else:
            return f"Error: Currency '{target}' not found in exchange rates."
            
    except Exception as e:
        return f"Error fetching exchange rate: {str(e)}"
    

@tool
def get_dnd_info(category: str, item_name: str = None) -> str:
    """
    Retrieves information from the D&D 5th Edition API (SRD content).

    Args:
        category: The category to search (e.g., 'monsters', 'spells', 'classes', 'races', 'equipment').
        item_name: (Optional) The specific name of the item to retrieve (e.g., 'fireball', 'adult-black-dragon').
                   If omitted, returns a list of all items in that category.

    Returns:
        str: The details of the requested D&D item or a list of items.
    """
    base_url = "https://www.dnd5eapi.co/api"
    clean_category = category.strip().lower()
    
    if item_name:
        # The API requires "slugified" indexes (e.g. "Mage Hand" -> "mage-hand")
        clean_name = item_name.strip().lower().replace(" ", "-")
        url = f"{base_url}/{clean_category}/{clean_name}"
    else:
        url = f"{base_url}/{clean_category}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return str(data)
        elif response.status_code == 404:
            return f"Error: Could not find '{item_name}' in category '{clean_category}'. Check spelling or try listing the category first."
        else:
            return f"Error: API returned status code {response.status_code}"
    except Exception as e:
        return f"Error fetching D&D data: {str(e)}"
      
# --- AGENT SETUP ---
model = LiteLLMModel(model_id="gpt-4o-mini", api_base="https://api.openai.com/v1")
agent = ToolCallingAgent(
    tools=[get_my_files, tavily_search, get_weather_info, get_stock_price, currency_exchange_tool, get_dnd_info],
    model=model,
    add_base_tools=False
)

# --- WEB ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

conversation_history = []

@app.route('/ask', methods=['POST'])
def ask_agent():
    user_input = request.form.get('query')
    if not user_input:
        return jsonify({"response": "Please enter a valid query."})
    
    try:
        # 1. Construct the Context from History
        # We format previous messages so the AI knows what happened before.
        history_text = ""
        for turn in conversation_history:
            history_text += f"User: {turn['user']}\nAI: {turn['ai']}\n"

        # 2. Create the "Memory-Aware" Prompt
        # We tell the AI to look at the history before answering.
        full_prompt = f"""
        Here is the conversation history so far:
        {history_text}

        Current User Request: {user_input}
        
        Answer the request. If the request refers to 'it' or 'that', use the history to understand what they mean.
        """

        # 3. Run the Agent with the Context
        # We pass the full_prompt instead of just user_input
        agent_response = agent.run(full_prompt)
        response_string = str(agent_response)

        # 4. Save this turn to History
        conversation_history.append({
            'user': user_input, 
            'ai': response_string
        })

        return jsonify({"response": response_string})

    except Exception as e:
        return jsonify({"response": f"An error occurred: {str(e)}"})

# Add a route to clear memory so you can start over
@app.route('/reset', methods=['POST'])
def reset_memory():
    global conversation_history
    conversation_history = []
    return jsonify({"status": "Memory cleared"})
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)