# auth/services/ai_service.py (FINAL - Official Library with DNS Fix)
import os
import google.generativeai as genai

# This will store the initialized model.
model = None

# --- Configuration ---
try:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY is not set!")
    
    # Use the official library's configuration method
    genai.configure(api_key=api_key) # type: ignore
    
    # Use the stable model name that works with this library
    model = genai.GenerativeModel('gemini-2.0-flash') # type: ignore

    print("INFO: Google AI Model 'gemini-2.0-flash' initialized successfully.")

except Exception as e:
    print(f"--- FATAL GOOGLE AI ERROR during initialization ---\n{repr(e)}\n--- END RAW ERROR ---")

# --- Main Functions ---
async def summarize_text(text_to_summarize: str) -> str:
    if not model:
        return "Error: The AI model is not initialized. Please check the backend terminal for initialization errors."
    if not text_to_summarize.strip(): 
        return "Error: No text was provided to summarize."
        
    try:
        prompt = f"Summarize the key points and any action items from the following email content in 3 concise bullet points:\n\n---\n{text_to_summarize}\n---"
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during summarization ---\n{repr(e)}\n--- END RAW ERROR ---")
        return "Error: Could not generate summary. Check backend logs for the raw error from Google."

async def generate_reply(prompt: str) -> str:
    if not model:
        return "Error: The AI model is not initialized. Check server logs."
    if not prompt.strip(): 
        return "Error: No prompt provided for reply generation."
        
    try:
        full_prompt = f"You are a professional assistant. Your task is to: {prompt}. Generate the full body of the email reply."
        response = await model.generate_content_async(full_prompt)
        return response.text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during reply generation ---\n{repr(e)}\n--- END RAW ERROR ---")
        return "Error: Could not generate reply. Check logs."