from typing import List
import json
from llama_cpp import Llama

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

# <------------- Local LLM setup start ----------->
LLM_PATH = "./models/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"
# LLM_PATH = "./models/Nous-Hermes-13B.Q4_K_M.gguf"

llm = Llama(
    model_path=LLM_PATH,
    n_ctx=2048,
    n_threads=8,  # Adjust based on your CPU
    use_mlock=True,
)   

def evaluate_rules_with_local_llm(transcript: str, rules: List[str]) -> List[dict]:
    prompt = build_gpt_prompt(transcript, rules)

    def call_llm():
        try:
            stream_response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a JSON extraction engine."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                max_tokens=1000,
                temperature=0.1
            )
            # Stream and accumulate output
            output_chunks = []
            for chunk in stream_response:
                if 'choices' in chunk and 'delta' in chunk['choices'][0]:
                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta:
                        output_chunks.append(delta['content'])

            return ''.join(output_chunks).strip()
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {str(e)}")

    # First attempt
    output = call_llm()

    # Retry once if blank output
    if not output:
        # print("[⚠️ Retry] Local LLM returned empty output. Retrying once...")
        output = call_llm()

    try:
        # Log output
        # print("\n[LLM RAW OUTPUT START]\n", output, "\n[LLM RAW OUTPUT END]")

        # Attempt to parse
        parsed = json.loads(output)

        # Validate structure
        if not isinstance(parsed, list):
            raise ValueError("Parsed LLM output is not a list")
        for item in parsed:
            if not isinstance(item, dict) or not all(k in item for k in ["rule", "result", "reason"]):
                raise ValueError(f"Invalid item structure in: {item}")

        return parsed

    except Exception as e:

        return [{
            "rule": rule,
            "result": "Error",
            "reason": f"LLM parsing failed: {str(e)}"
        } for rule in rules]

# <-------------- Local LLM setup end ----------->
