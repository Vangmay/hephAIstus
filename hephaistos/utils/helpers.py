import json 
import os 

def safe_path(workspace, path) -> str:
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Access to parent directories ('../') is not allowed.")
    abs_path = os.path.abspath(os.path.join(workspace, path))
    return abs_path

def _clip(s, n=4000):
    return s if len(s) <= n else s[:n] + "\n...[truncated]"

def _parse_json(txt: str) -> dict:
    txt = txt.strip()
    # Remove code fences if present
    if txt.startswith("```") and txt.endswith("```"):
        txt = txt.strip("`").strip()
    # Find first '{' and last '}'
    start = txt.find("{")
    end = txt.rfind("}")
    if start != -1 and end != -1 and end > start:
        txt = txt[start:end+1]
    try:
        obj = json.loads(txt)
        # Validate shape
        if "thought" in obj and ("action" in obj or "final" in obj):
            return obj
        else:
            return {"thought": "Parse error: missing required keys.", "action": None, "final": None}
    except Exception as e:
        return {"thought": f"JSON parse error: {e}\nRaw: {txt[:500]}", "action": None, "final": None}
