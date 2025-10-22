# backend/services/ai_service.py (FINAL - Intelligent Regeneration)
import os
import json
import google.generativeai as genai

model = None
try:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY is not set!")
    
    genai.configure(api_key=api_key) # type: ignore
    model = genai.GenerativeModel('gemini-2.0-flash') # type: ignore

    print("INFO: Google AI Model 'gemini-2.0-flash' initialized successfully.")

except Exception as e:
    print(f"--- FATAL GOOGLE AI ERROR during initialization ---\n{repr(e)}\n--- END RAW ERROR ---")

async def summarize_text(text_to_summarize: str) -> str:
    if not model:
        return json.dumps({"error": "The AI model is not initialized."})
    if not text_to_summarize.strip():
        return json.dumps({"error": "No text was provided to summarize."})

    prompt = f"""
    Analyze the following email content and extract key information.
    Your response must be ONLY a single, raw JSON object. Do not include markdown formatting (like ```json ... ```).
    
    The JSON object must have this exact structure:
    {{
        "summary": "A detailed, insightful, and professionally toned paragraph summarizing the email's core message.",
        "action_items": ["A list of specific, actionable tasks for the user. Be precise.", "Example: 'Review the revised pricing schedule before November 17th.'"],
        "key_dates": ["A list of important dates or deadlines mentioned.", "Example: 'Nov 17, 2025: New pricing takes effect.'"]
    }}

    If any field is not applicable, return an empty list [].
    Do not invent information. Your analysis must be based solely on the text provided.
    
    ---EMAIL CONTENT TO ANALYZE---
    {text_to_summarize}
    ---END EMAIL CONTENT---
    """
        
    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text
        clean_json_text = raw_text.replace("```json", "").replace("```", "").strip()
        json.loads(clean_json_text)
        return clean_json_text

    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during summarization ---\n{repr(e)}\n--- END RAW ERROR ---")
        return json.dumps({
            "summary": "Error: Could not generate a summary. The AI API returned an error.",
            "action_items": [], "key_dates": [], "error": "true"
        })

# --- THIS IS THE UPGRADED, INTELLIGENT DRAFTING FUNCTION ---
async def generate_reply(prompt: str) -> str:
    if not model:
        return "Error: The AI model is not initialized."
    if not prompt.strip():
        return "Error: No prompt was provided for reply generation."

    # Check if this is a regeneration request
    if "different version" in prompt:
        system_instruction = "You are an expert email assistant. A user has requested a different version of a draft. Your task is to re-write the email based on the original context, but with a different tone or structure. DO NOT explain what you are doing or provide multiple options. Just provide the single, new, complete email draft."
    else:
        system_instruction = "You are an expert email assistant. Your task is to draft a professional and helpful email reply based on the provided context. Generate the full body of the email. Do not include the 'Subject:' line."

    # We now create a new model instance for each call to apply the system instruction
    instructed_model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=system_instruction
    )
        
    try:
        response = await instructed_model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"--- RAW GOOGLE AI ERROR during reply generation ---\n{repr(e)}\n--- END RAW ERROR ---")
        return "Error: Could not generate reply. Check logs."