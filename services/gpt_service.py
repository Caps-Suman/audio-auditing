from typing import List
import openai
import os, json
from openai import OpenAI
from dotenv import load_dotenv

from llama_cpp import Llama
import json
import os

EXTRACTION_PROMPT_TEMPLATE = """
You are a JSON-only extraction engine. Your task is to extract and return strictly the following fields in minified JSON format from the given call transcript.

Required fields:
- claim_status (string: "approved", "denied", "pending", "under_appeal")
- denial_reason (string or null)
- authorization_number (string)
- next_followup (string)
- agent_summary (string — summarize the agent's explanation or instructions in 1-2 sentences)
- customer_summary (string — summarize the customer's main intent, question, or concern in 1-2 sentences)

Rules:
- Return ONLY valid JSON — no explanations, markdown, or commentary.
- Format must be minified JSON — no line breaks, indentation, or extra whitespace.
- If a field is not present in the conversation, use null or empty string appropriately.
- Summaries should be concise and reflect what was said or asked.

Expected output format:
{"claim_status":"...","denial_reason":"...","authorization_number":"...","next_followup":"...","agent_summary":"...","customer_summary":"..."}

Transcript:
"""

def build_gpt_prompt(transcript: str, rule_list: list[str]) -> str:
    formatted_rules = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(rule_list)])

    prompt = f"""
                You are a quality audit evaluation engine.

                Your task is to analyze a call transcript and determine whether each of the provided rules is satisfied based on what was said in the call.

                Instructions:
                - For each rule, return:
                - "rule": the rule text
                - "result": "Yes" if the rule was followed, "No" if not, "Unknown" if not verifiable
                - "reason": briefly justify the answer (1-2 sentences max)
                - Use ONLY the information found in the transcript.
                - Do NOT assume or hallucinate anything.
                - Return only a valid JSON array (no markdown, no commentary).

                Rules:
                {formatted_rules}

                Transcript:
                \"\"\"{transcript}\"\"\"

                Return format (strict JSON):
                [
                {{
                    "rule": "...",
                    "result": "Yes" | "No" | "Unknown",
                    "reason": "..."
                }},
                ...
                ]
                """
    return prompt.strip()

# <-------------- OpenAI setup start ----------->
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def evaluate_rules_with_gpt(transcript: str, rules: List[str]) -> List[dict]:
    prompt = build_gpt_prompt(transcript, rules)

    try:
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800
        )
        result_text = response['choices'][0]['message']['content']
        return json.loads(result_text)
    except Exception as e:
        return [{"rule": rule, "result": "Error", "reason": str(e)} for rule in rules]
    

def extract_audit_fields_from_text_using_openai(transcript: str) -> dict:
    prompt = EXTRACTION_PROMPT_TEMPLATE + transcript + "\n\nReturn only valid JSON."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500
    )

    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        return {"raw_output": content}

# <-------------- OpenAI setup end ----------->

# <------------- Local LLM setup start ----------->
# LLM_PATH = "./models/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"
LLM_PATH = "./models/Nous-Hermes-13B.Q4_K_M.gguf"

llm = Llama(
    model_path=LLM_PATH,
    n_ctx=2048,
    n_threads=8,  # Adjust based on your CPU
    use_mlock=True,
)

def extract_audit_fields_from_text_using_local_llm(transcript: str) -> dict:
    try:
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a JSON extraction engine."},
                {"role": "user", "content": EXTRACTION_PROMPT_TEMPLATE + transcript}
            ],
            max_tokens=512
        )
        output = response["choices"][0]["message"]["content"].strip()
        return json.loads(output)
    except Exception as e:
        return {"raw_output": output if 'output' in locals() else '', "error": str(e)}

# <-------------- Local LLM setup end ----------->
