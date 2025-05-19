from typing import List
import os, json
from dotenv import load_dotenv
from fastapi import logger
from openai import OpenAI
import requests

def build_gpt_prompt(transcript: str, rule_list: list[str]) -> str:
    # formatted_rules = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(rule_list)])
    cleaned_rules = [rule.replace('\n', ' ') for rule in rule_list]
    formatted_rules = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(cleaned_rules)])

    prompt = f"""
                You are a quality audit evaluation engine.

                Your task is to analyze a call transcript and determine whether each of the provided rules is satisfied based on what was said in the call.

                Instructions:
                - For each rule, return:
                - "rule": the exact rule text (must match input exactly)
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

# <-------------- OpenAI setup using API ----------->

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
        "max_tokens": 1000,
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


# <-------------- OpenAI setup using SDK ----------->
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    project=os.getenv("OPENAI_PROJECT_ID")
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

# <-------------- OpenAI setup end ----------->

