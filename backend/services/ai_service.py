# backend/services/ai_service.py (FINAL - With Thread Logic)
import os
import json
import google.generativeai as genai

model = None
try:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key: raise ValueError("GOOGLE_AI_API_KEY is not set!")
    genai.configure(api_key=api_key) # type: ignore
    model = genai.GenerativeModel('gemini-2.0-flash') # type: ignore
    print("INFO: Google AI Model 'gemini-2.0-flash' initialized successfully.")
except Exception as e:
    print(f"--- FATAL GOOGLE AI ERROR ---\n{repr(e)}\n---")

async def summarize_text(text_to_summarize: str, is_thread: bool = False) -> str:
    if not model: return json.dumps({"error": "AI model not initialized."})
    if not text_to_summarize.strip(): return json.dumps({"error": "No text provided."})

    # This is the new logic to handle both single emails and threads
    if is_thread:
        prompt = f"""
        Analyze the following email thread, which is presented in chronological order.
        Create a narrative summary that tells the story of the conversation.
        Your response must be ONLY a single, raw JSON object with this structure:
        {{"summary": "A chronological story of the conversation.", "action_items": ["A consolidated list of all unresolved action items."], "key_dates": ["A consolidated list of all upcoming dates."]}}
        
        ---EMAIL THREAD---
        {text_to_summarize}
        ---END THREAD---
        """
    else:
        prompt = f"""
        Analyze the following email and extract key information.
        Your response must be ONLY a single, raw JSON object with this structure:
        {{"summary": "A detailed paragraph summary.", "action_items": ["A list of tasks."], "key_dates": ["A list of dates."]}}
        
        ---EMAIL CONTENT---
        {text_to_summarize}
        ---END CONTENT---
        """
    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        json.loads(raw_text)
        return raw_text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR ---\n{repr(e)}\n---")
        return json.dumps({"summary": "Error: Could not generate summary.", "action_items": [], "key_dates": [], "error": "true"})

async def generate_reply(prompt: str, persona: str) -> str:
    if not model: return "Error: AI model not initialized."
    if not prompt.strip(): return "Error: No prompt provided."
    system_instruction = f'You are an expert email assistant. Your persona is: "{persona}". Your task is to draft a complete, professional email reply based on the context. Your response MUST be ONLY the body of the email. DO NOT include "Subject:" or any conversational text.'
    instructed_model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=system_instruction) # type: ignore
    try:
        response = await instructed_model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR ---\n{repr(e)}\n---")
        return "Error: Could not generate reply. Check logs."