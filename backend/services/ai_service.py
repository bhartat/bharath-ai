# backend/services/ai_service.py (FINAL - Definitive with Executive Briefing)
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
    if not model: return json.dumps({"error": "The AI model is not initialized."})
    if not text_to_summarize.strip(): return json.dumps({"error": "No text was provided to summarize."})

    # This is the new logic to handle both single emails and threads
    if is_thread:
        prompt = f"""
        You are an expert executive assistant. Analyze the following email thread and provide a concise "Executive Briefing".
        Your response MUST be ONLY a single, raw JSON object. Do not include markdown.
        
        The JSON object must have this exact structure:
        {{
            "summary": "A chronological narrative of the conversation, explaining who said what and what the final outcome was.",
            "action_items": ["A consolidated list of all unresolved action items from the entire thread."],
            "key_dates": ["A consolidated list of all upcoming dates or deadlines mentioned."],
            "participants": ["A list of the names of everyone involved in the conversation."]
        }}

        - For "summary", tell the story of the conversation from start to finish.
        - For "participants", only list the names, not the email addresses.
        - If a field is not applicable, return an empty list [].
        
        ---EMAIL THREAD TO ANALYZE---
        {text_to_summarize}
        ---END THREAD---
        """
    else:
        prompt = f"""
        Analyze the following email content and extract key information.
        Your response must be ONLY a single, raw JSON object.
        The JSON object must have this exact structure:
        {{"summary": "A detailed paragraph summary.", "action_items": [], "key_dates": []}}
        
        ---EMAIL CONTENT TO ANALYZE---
        {text_to_summarize}
        ---END EMAIL CONTENT---
        """
    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        json.loads(raw_text) # Validate it's proper JSON
        return raw_text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during summarization ---\n{repr(e)}\n--- END RAW ERROR ---")
        return json.dumps({"summary": "Error: Could not generate a summary.", "action_items": [], "key_dates": [], "participants": [], "error": "true"})

async def generate_reply(prompt: str, persona: str) -> str:
    if not model: return "Error: The AI model is not initialized."
    if not prompt.strip(): return "Error: No prompt provided."

    if "different version" in prompt:
        system_instruction = f"""You are an expert email assistant rewriting a draft.
        Your task is to re-write the email based on the original context, but with a different tone or structure.
        You MUST adopt the following persona for your writing style: "{persona}"
        Generate only the full, complete body of the new email draft. DO NOT add any commentary.
        """
    else:
        system_instruction = f"""You are an expert email assistant. Your task is to draft a professional and helpful email reply.
        You MUST adopt the following persona for your writing style: "{persona}"
        Generate only the full body of the email. Do not include the 'Subject:' line.
        """

    instructed_model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=system_instruction) # type: ignore
        
    try:
        response = await instructed_model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during reply generation ---\n{repr(e)}\n--- END RAW ERROR ---")
        return "Error: Could not generate reply. Check logs."