import asyncio
from typing import Dict, List
import os, json
from dotenv import load_dotenv
from fastapi import logger
from openai import AsyncOpenAI, OpenAI
import requests

def build_gpt_prompt(transcript: str, rule_list: list[str]) -> str:
    # print("Input rules to GPT:", rule_list)
    formatted_rules = "\n".join([
        f"{i+1}. [ID: {r['ruleId']}] {r['rule']}"
        for i, r in enumerate(rule_list)
    ])

    # - IMPORTANT: If a rule explicitly says to default to "Yes" or "No" in case of **missing information**, you must follow that instruction.
    prompt = f"""
                You are a quality audit evaluation engine.

                Your task is to analyze a call transcript and determine whether each of the provided rules is satisfied based on what was said in the call.

                Instructions:
                - For each rule, return:
                    - "ruleId": the rule's unique ID
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
                    "ruleId": "ruleId",
                    "rule": "...",
                    "result": "Yes" | "No" | "Unknown",
                    "reason": "..."
                }},
                ...
                ]
                """
    return prompt.strip()

# <-------------- OpenAI setup, without confidence score start ----------->

load_dotenv()
api_key = os.getenv("api_key")
project_id = os.getenv("OPENAI_PROJECT_ID")

def evaluate_rules_with_gpt_using_requests(transcript: str, rules: List[str]) -> List[dict]:
    prompt = build_gpt_prompt(transcript, rules)

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.1
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if project_id:
        headers["OpenAI-Project"] = project_id

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code != 200:
        print("API Error:", response.status_code, response.text)
        return [{"rule": rule, "result": "Error", "reason": response.text} for rule in rules]

    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return [{"rule": rule, "result": "Error", "reason": f"Parsing error: {str(e)}"} for rule in rules]
# <-------------- OpenAI setup, without confidence score end ----------->


# <-------------- OpenAI setup, response with confidence score start ----------->
def build_gpt_prompt_with_confidence(transcript: str, rule_list: List[Dict[str, str]]) -> str:
    formatted_rules = "\n".join([
        f"{i+1}. [ID: {r['ruleId']}] {r['rule']}"
        for i, r in enumerate(rule_list)
    ])

    prompt = f"""
        You are a quality audit evaluation engine.

        Your task is to analyze a call transcript and determine whether each of the provided rules is satisfied based on what was said in the call.

        Instructions:
        - For each rule, return:
            - "ruleId": the unique ID of the rule
            - "result": one of "Yes", "No", or "Unknown"
            - "reason": a brief explanation of your decision (1-2 sentences)
            - "confidenceScore": a float between 0.0 and 1.0 indicating how confident you are in the result
        - Use only the information found in the transcript. Do not hallucinate or make assumptions.

        Rules:
        {formatted_rules}

        Transcript:
        \"\"\"{transcript}\"\"\"

        Return format (strict JSON):
        [
        {{
            "ruleId": "...",
            "rule": "...",
            "result": "Yes" | "No" | "Unknown",
            "reason": "...",
            "confidenceScore": 0.0 - 1.0
        }},
        ...
        ]
        """
    return prompt.strip()

def evaluate_rules_with_gpt_using_requests_with_confidence(transcript: str, rule_list: List[Dict[str, str]]) -> List[dict]:
    prompt = build_gpt_prompt_with_confidence(transcript, rule_list)

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1500
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if project_id:
        headers["OpenAI-Project"] = project_id

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code != 200:
        print("API Error:", response.status_code, response.text)
        return [{
            "ruleId": rule["ruleId"],
            "rule": rule["rule"],
            "result": "Error",
            "reason": response.text,
            "confidenceScore": 0.0
        } for rule in rule_list]

    try:
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        # Validate and normalize confidenceScore
        for item in parsed:
            try:
                score = float(item.get("confidenceScore", 0.5))
                item["confidenceScore"] = max(0.0, min(score, 1.0))
            except Exception:
                item["confidenceScore"] = 0.5  # fallback if malformed

        return parsed

    except Exception as e:
        return [{
            "ruleId": rule["ruleId"],
            "rule": rule["rule"],
            "result": "Error",
            "reason": f"Parsing error: {str(e)}",
            "confidenceScore": 0.0
        } for rule in rule_list]

# <-------------- OpenAI setup, with confidence score end ----------->

# <--------------- Diarization and HTML formatting using openai API---------------->
def format_transcript_html_with_gpt_using_requests(segments: List[dict]) -> str:
    """
    Uses OpenAI API to convert Whisper segments into speaker-tagged HTML blocks.
    """
    # Helper to format timestamps
    def seconds_to_timestamp(seconds: float) -> str:
        import datetime
        return str(datetime.timedelta(seconds=int(seconds)))

    # Prepare transcript block
    raw_transcript = "\n".join([
        f"[{seconds_to_timestamp(seg['start'])}] {seg['text'].strip()}"
        for seg in segments
    ])

    # Prompt to instruct GPT to infer speakers and return HTML
    prompt = f"""
            You are a formatting assistant. Given a list of time-stamped call transcript lines, return HTML-formatted output as specified.

            Instructions:
            - Each line starts with a timestamp like [00:00:05]
            - Based on the line content, infer whether the speaker is an Agent or a Customer
            - Use "assistantClass" for Agent and "userClass" for Customer
            - Default to Agent if unsure
            - Format each line as:

            <div class="{{className}}">
            <span class="timeClass">[timestamp]</span>
            <span class="speakerClass">{{Agent|Customer}}: </span>
            <span class="textClass">{{spoken text}}</span>
            </div>

            Return only the complete HTML content. No commentary, markdown, or code fences.

            Transcript:
            \"\"\"{raw_transcript}\"\"\"
            """

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.1
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if project_id:
        headers["OpenAI-Project"] = project_id

    # Call OpenAI API
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        print("API Error:", response.status_code, response.text)
        return f"<!-- Error: {response.text} -->"

    try:
        html_output = response.json()["choices"][0]["message"]["content"]
        return html_output.strip()
    except Exception as e:
        return f"<!-- Parsing error: {str(e)} -->"


# <-------------- OpenAI setup using SDK (Sync) ----------->
client = OpenAI(
    api_key=os.getenv("api_key"),
    project=os.getenv("OPENAI_PROJECT_ID")
)
    
def evaluate_rules_with_gpt_using_sdk_with_confidence(transcript: str, rule_list: List[Dict[str, str]]) -> List[dict]:
    prompt = build_gpt_prompt_with_confidence(transcript, rule_list)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Normalize confidenceScore
        for item in parsed:
            try:
                score = float(item.get("confidenceScore", 0.5))
                item["confidenceScore"] = max(0.0, min(score, 1.0))
            except Exception:
                item["confidenceScore"] = 0.5  # Fallback

        return parsed

    except Exception as e:
        print("LLM Evaluation Error:", e)
        return [{
            "ruleId": rule["ruleId"],
            "rule": rule["rule"],
            "result": "Error",
            "reason": f"Exception: {str(e)}",
            "confidenceScore": 0.0
        } for rule in rule_list]

# <-------------- OpenAI setup end (Sync) ----------->


# <-------------- OpenAI setup using SDK (Async) ---------->
async_client = AsyncOpenAI(
    api_key=os.getenv("api_key"),
    project=os.getenv("OPENAI_PROJECT_ID")
)

async def evaluate_rules_with_gpt_using_sdk_with_confidence_async(
    transcript: str,
    rule_list: List[Dict[str, str]]
) -> List[dict]:
    prompt = build_gpt_prompt_with_confidence(transcript, rule_list)

    try:
        response = await async_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Normalize confidenceScore
        for item in parsed:
            try:
                score = float(item.get("confidenceScore", 0.5))
                item["confidenceScore"] = max(0.0, min(score, 1.0))
            except Exception:
                item["confidenceScore"] = 0.5

        return parsed

    except Exception as e:
        print("LLM Async Error:", e)
        return [{
            "ruleId": rule["ruleId"],
            "rule": rule["rule"],
            "result": "Error",
            "reason": f"Exception: {str(e)}",
            "confidenceScore": 0.0
        } for rule in rule_list]
    

async def evaluate_param_with_rules(transcript: str, param) -> Dict:
    rule_list = [{"ruleId": r.ruleId, "rule": r.rule.strip()} for r in param.ruleList]
    rule_map = {r["ruleId"]: r["rule"] for r in rule_list}
    prompt = build_gpt_prompt_with_confidence(transcript, rule_list)

    try:
        response = await async_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        for item in parsed:
            try:
                score = float(item.get("confidenceScore", 0.5))
                item["confidenceScore"] = max(0.0, min(score, 1.0))
            except Exception:
                item["confidenceScore"] = 0.5

            item["rule"] = rule_map.get(item["ruleId"], "[Rule Missing]")

        return {"id": param.id, "name": param.name, "rules": parsed}

    except Exception as e:
        print(f"GPT error for param {param.name}: {e}")
        return {
            "id": param.id,
            "name": param.name,
            "rules": [{
                "ruleId": r["ruleId"],
                "rule": r["rule"],
                "result": "Error",
                "reason": str(e),
                "confidenceScore": 0.0
            } for r in rule_list]
        }

async def evaluate_all_parameters_async(transcript: str, parameters: List) -> List[Dict]:
    tasks = [evaluate_param_with_rules(transcript, param) for param in parameters]
    return await asyncio.gather(*tasks)
    
# <-------------- OpenAI setup using SDK (Async) end ----------->
