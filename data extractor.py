import os
import time
import json
import random
import re
import requests
import pandas as pd
import csv
from io import StringIO

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Set OPENAI_API_KEY as API in env"

#USING THE FILE ID THAT IS UPLOADED TO OPENAI
FILE_ID = "file-B4Pco3TY8DbwttGt8QABuf"  
MODEL = "gpt-5-nano"                 #change if you need another model you have access to

QUESTION = """ #
Extract ALL structured information from the document and return ONLY a CSV. 
No explanations, no markdown, no JSON - just clean CSV.

The CSV must have EXACTLY these columns:
KEY,VALUE,COMMENTS,PAGE

CRITICAL RULES:
- Extract EVERY piece of information including: personal details, education, work history, salaries, certifications, technical skills, dates, locations, scores, and any other data points.
- KEY must be a descriptive canonical label. Use specific labels like:
  name, birth_date, birth_place, age, nationality, blood_group, 
  education_high_school, education_bachelor, education_master, 
  current_job, previous_job, current_employer, previous_employer,
  salary_current, salary_previous, salary_first,
  certification_aws, certification_azure, certification_pmp, certification_safe,
  skill_sql, skill_python, skill_machine_learning, skill_cloud, skill_data_visualization,
  work_start_date, work_end_date, promotion_date,
  exam_scores, thesis_score, academic_rank, graduation_year
  ...and any other relevant fields you find.

- VALUE must be the exact text snippet or specific value from the document.
- COMMENTS should contain ISO dates when applicable (iso:YYYY-MM-DD) or brief context.
- PAGE should be 1 since it's a single-page document.
- DO NOT summarize or combine information - create separate rows for each distinct data point.
- Include ALL dates, scores, percentages, and numerical values.
- Extract technical skill ratings and years of experience.
- Extract complete education history with institutions, degrees, scores, and years.
- Extract complete work history with companies, roles, salaries, and dates.
- Extract ALL certification details with scores and dates.

Example output format (literal CSV):
KEY,VALUE,COMMENTS,PAGE
name,Vijay Kumar,,
birth_date,born on March 15, 1989,iso:1989-03-15,1
birth_place,Jaipur, Rajasthan,,
age,35 years old as of 2024,,
education_high_school,St. Xavier's School, Jaipur,completed 12th standard in 2007,1
high_school_score,92.5%,overall score in board examinations,1
education_bachelor,B.Tech in Computer Science at IIT Delhi,graduated with honors in 2011,1
bachelor_cgpa,8.7,on 10-point scale,1
bachelor_rank,15th among 120 students,,
skill_sql,10 out of 10,daily usage since 2012,1

Extract EVERYTHING you find in the document.
""".strip()

RESPONSES_URL = "https://api.openai.com/v1/responses"
HEADERS = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

MAX_RETRIES = 6
BASE_WAIT = 1.0

def flatten_json(prefix, obj, rows):
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_json(f"{prefix}.{k}" if prefix else k, v, rows)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            flatten_json(f"{prefix}[{i}]", item, rows)
    else:
        rows.append((prefix, obj))

def extract_csv_from_text(text):
    """Extract CSV data from text and return as DataFrame"""
    lines = text.strip().split('\n')
    csv_lines = []
    in_csv = False
    
    for line in lines:
        
        if line.startswith('KEY,VALUE,COMMENTS,PAGE'):
            in_csv = True
            csv_lines = [line]
            continue
        elif in_csv:
            #Stop if we hit a non-CSV line
            if not line or ',' not in line or line.startswith('---'):
                break
            csv_lines.append(line)
    
    if len(csv_lines) > 1:
        csv_text = '\n'.join(csv_lines)
        return pd.read_csv(StringIO(csv_text))
    return None

def call_responses_with_file(file_id):
    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": file_id},
                    {"type": "input_text", "text": QUESTION},
                ],
            }
        ],
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(RESPONSES_URL, headers=HEADERS, json=payload, timeout=120)
        except requests.RequestException as e:
            wait = BASE_WAIT * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(f"[attempt {attempt}] network error: {e}. backing off {wait:.1f}s")
            time.sleep(wait)
            continue

        print(f"[attempt {attempt}] STATUS: {resp.status_code}")
        print(f"[attempt {attempt}] BODY preview: {resp.text[:2000]}")

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    wait = int(ra)
                except:
                    wait = BASE_WAIT * (2 ** (attempt - 1))
            else:
                wait = BASE_WAIT * (2 ** (attempt - 1)) + random.uniform(0, 1.0)
            print(f"[attempt {attempt}] 429. Waiting {wait:.1f}s")
            time.sleep(wait)
            continue
        if 500 <= resp.status_code < 600:
            wait = BASE_WAIT * (2 ** (attempt - 1)) + random.uniform(0, 1.0)
            print(f"[attempt {attempt}] server error {resp.status_code}. waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        #return parsed error JSON for inspection
        try:
            return resp.json()
        except Exception:
            return {"error": {"message": resp.text, "status_code": resp.status_code}}

    raise SystemExit(f"Failed after {MAX_RETRIES} attempts due to repeated 429/5xx errors.")

def main():
    resp_json = call_responses_with_file(FILE_ID)

    if isinstance(resp_json, dict) and resp_json.get("error"):
        print("API returned error:", json.dumps(resp_json, indent=2))
        raise SystemExit("Exiting due to API error.")

    print("\n=== Full response (trimmed) ===")
    print(json.dumps(resp_json, indent=2)[:4000])

    # extract text blocks
    extracted_texts = []
    outputs = resp_json.get("output") or resp_json.get("results") or []
    if isinstance(outputs, dict):
        outputs = [outputs]
    for o in outputs:
        content = o.get("content") or o.get("text") or o
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and "text" in block:
                        extracted_texts.append(block.get("text"))
                    elif "text" in block:
                        extracted_texts.append(block.get("text"))
                    elif "content" in block and isinstance(block["content"], str):
                        extracted_texts.append(block["content"])
                    else:
                        extracted_texts.append(json.dumps(block))
                else:
                    extracted_texts.append(str(block))
        elif isinstance(content, str):
            extracted_texts.append(content)
        else:
            extracted_texts.append(json.dumps(content))

    if extracted_texts:
        for i, t in enumerate(extracted_texts, 1):
            print(f"\n--- Block {i} ---\n{t[:3000]}")

    # flatten and write full response to Excel
    rows = []
    flatten_json("", resp_json, rows)
    df = pd.DataFrame(rows, columns=["path", "value"])
    flat_excel = "response_output_flat.xlsx"
    df.to_excel(flat_excel, index=False)
    print(f"\nFlattened response written to: {flat_excel}")

    #NEW: Extract and save CSV data
    csv_data_found = False
    for text in extracted_texts:
        if "KEY,VALUE,COMMENTS,PAGE" in text:
            csv_df = extract_csv_from_text(text)
            if csv_df is not None:
                csv_output = "extracted_data.csv"
                csv_df.to_csv(csv_output, index=False)
                print(f"Extracted CSV data written to: {csv_output}")
                
                # Also save as Excel for better formatting
                excel_output = "extracted_data.xlsx"
                csv_df.to_excel(excel_output, index=False)
                print(f"Extracted data written to: {excel_output}")
                
                print("\nExtracted Data:")
                print(csv_df.to_string(index=False))
                csv_data_found = True
                break
    
    if not csv_data_found:
        print("No CSV data found in response")

if __name__ == "__main__":
    main()