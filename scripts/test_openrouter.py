import os
import requests
import json
from dotenv import load_dotenv

def call_openrouter_api(prompt: str, model: str = "mistralai/mistral-7b-instruct:free") -> dict:
    """
    Calls the OpenRouter API with a given prompt and model.
    """
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Error: OPENROUTER_API_KEY not found in environment variables.")

    api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(api_url, headers=headers, json=data)
    
    # Raise an exception for bad status codes
    response.raise_for_status()
    
    return response.json()

def main():
    try:
        model = "mistralai/mistral-7b-instruct:free"
        prompt = "What are the top 3 benefits of using Python?"
        print(f"Sending request to model: {model}...")
        
        response_json = call_openrouter_api(prompt, model)
        ai_message = response_json['choices'][0]['message']['content']
        
        print("\n--- API Call Successful ---")
        print("Status Code: 200")
        print("\nAI Response:")
        print(ai_message)
        print("\n--------------------------\n")
        
    except requests.exceptions.HTTPError as http_err:
        print(f"\n--- API Call Failed ---")
        print(f"HTTP Error: {http_err}")
        try:
            # Try to print the detailed JSON error response
            print("Response Body:")
            print(json.dumps(http_err.response.json(), indent=2))
        except ValueError:
            print("Response Body:")
            print(http_err.response.text)
        print("\n-----------------------\n")
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
