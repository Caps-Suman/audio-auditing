from typing import List
import os, json
from fastapi import logger
from openai import OpenAI
from dotenv import load_dotenv
# import datetime
import json
# from llama_cpp import Llama
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
client = OpenAI(
    # api_key=os.getenv("OPENAI_API_KEY"),
    # organization=os.getenv("ORGANIZATION_ID"),
    # project=os.getenv("PROJECT_ID")

    api_key="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",
    organization="org-Xl0FwsRYQBZYwJNwm820gOlA",
    project="proj_cFBBKgTs77izV9JiATa7W5o0"
)

def evaluate_rules_with_gpt(sampleId: int,transcript: str, rules: List[str]) -> List[dict]:
    prompt = build_gpt_prompt(transcript, rules)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4o" for better reasoning
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )

        # Fix for new OpenAI SDK
        result_text = response.choices[0].message.content.strip()

        # Optional: Clean markdown wrappers if any
        result_text = result_text.strip('`').strip()
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            logger.warning("GPT returned invalid JSON", extra={"sampleId ": sampleId})    

    except Exception as e:
        return [{
            "rule": rule,
            "result": "Error",
            "reason": str(e)
        } for rule in rules]



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
# LLM_PATH = "./models/Nous-Hermes-13B.Q4_K_M.gguf"

# llm = Llama(
#     model_path=LLM_PATH,
#     n_ctx=2048,
#     n_threads=8,  # Adjust based on your CPU
#     use_mlock=True,
# )

# def extract_audit_fields_from_text_using_local_llm(transcript: str) -> dict:
#     try:
#         response = llm.create_chat_completion(
#             messages=[
#                 {"role": "system", "content": "You are a JSON extraction engine."},
#                 {"role": "user", "content": EXTRACTION_PROMPT_TEMPLATE + transcript}
#             ],
#             max_tokens=512
#         )
#         output = response["choices"][0]["message"]["content"].strip()
#         return json.loads(output)
#     except Exception as e:
#         return {"raw_output": output if 'output' in locals() else '', "error": str(e)}
    

# def evaluate_rules_with_local_llm(transcript: str, rules: List[str]) -> List[dict]:
#     prompt = build_gpt_prompt(transcript, rules)

#     def call_llm():
#         try:
#             stream_response = llm.create_chat_completion(
#                 messages=[
#                     {"role": "system", "content": "You are a JSON extraction engine."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 stream=True,
#                 max_tokens=1000,
#                 temperature=0.1
#             )
#             # Stream and accumulate output
#             output_chunks = []
#             for chunk in stream_response:
#                 if 'choices' in chunk and 'delta' in chunk['choices'][0]:
#                     delta = chunk['choices'][0]['delta']
#                     if 'content' in delta:
#                         output_chunks.append(delta['content'])

#             return ''.join(output_chunks).strip()
#         except Exception as e:
#             raise RuntimeError(f"LLM call failed: {str(e)}")

#     # First attempt
#     output = call_llm()

#     # Retry once if blank output
#     if not output:
#         # print("[⚠️ Retry] Local LLM returned empty output. Retrying once...")
#         output = call_llm()

#     try:
#         # Log output
#         # print("\n[LLM RAW OUTPUT START]\n", output, "\n[LLM RAW OUTPUT END]")

#         # Attempt to parse
#         parsed = json.loads(output)

#         # Validate structure
#         if not isinstance(parsed, list):
#             raise ValueError("Parsed LLM output is not a list")
#         for item in parsed:
#             if not isinstance(item, dict) or not all(k in item for k in ["rule", "result", "reason"]):
#                 raise ValueError(f"Invalid item structure in: {item}")

#         return parsed

#     except Exception as e:
#         # Append to central log
#         log_path = "llm_debug_log.txt"
#         with open(log_path, "a", encoding="utf-8") as f:
#             f.write("\n" + "=" * 80 + "\n")
#             f.write(f"🕒 Timestamp: {datetime.datetime.now().isoformat()}\n")
#             f.write("📥 Prompt:\n" + prompt + "\n")
#             f.write("📤 LLM Output:\n" + (output or "[Empty]") + "\n")
#             f.write("❌ Error:\n" + str(e) + "\n")

#         # print(f"[❌ Parsing Error] LLM output could not be parsed. Logged to {log_path}")

#         return [{
#             "rule": rule,
#             "result": "Error",
#             "reason": f"LLM parsing failed: {str(e)}"
#         } for rule in rules]

# <-------------- Local LLM setup end ----------->
