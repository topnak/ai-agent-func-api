import json
import os
import time
from typing import Any, Dict, List, Optional

import azure.functions as func
from azure.identity import DefaultAzureCredential, AzureAuthorityHosts
from azure.ai.projects import AIProjectClient

# --- Helpers -----------------------------------------------------------------

def _cors_headers() -> Dict[str, str]:
    allowed = os.environ.get("ALLOWED_ORIGINS", "*")
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": msg}),
        status_code=400,
        mimetype="application/json",
        headers=_cors_headers()
    )

def _server_error(msg: str, details: Optional[str] = None) -> func.HttpResponse:
    body = {"error": msg}
    if details:
        body["details"] = details
    return func.HttpResponse(
        json.dumps(body),
        status_code=500,
        mimetype="application/json",
        headers=_cors_headers()
    )

# --- Function entry -----------------------------------------------------------

async def main(req: func.HttpRequest) -> func.HttpResponse:
    # Handle preflight CORS
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_cors_headers())

    # Read config
    endpoint = os.environ.get("AZURE_AI_ENDPOINT")
    default_agent_id = os.environ.get("AZURE_AI_AGENT_ID")

    if not endpoint:
        return _server_error("Server missing AZURE_AI_ENDPOINT")
    if not default_agent_id:
        return _server_error("Server missing AZURE_AI_AGENT_ID")

    # Parse body
    try:
        body = req.get_json()
    except ValueError:
        return _bad_request("Invalid JSON body.")

    user_input: str = body.get("input", "Hi")
    agent_id: str = body.get("agentId", default_agent_id)
    # Optional config
    poll_interval_ms: int = int(body.get("pollIntervalMs", 1000))
    hard_timeout_ms: int = int(body.get("timeoutMs", 60000))  # 60s default

    # Create credential (DefaultAzureCredential works with SP, MI, or az login)
    try:
        # If you need a specific authority (e.g., Azure Gov), set AZURE_AUTHORITY_HOST env
        credential = DefaultAzureCredential()
        client = AIProjectClient(endpoint=endpoint, credential=credential)
    except Exception as e:
        return _server_error("Failed to initialize AIProjectClient.", str(e))

    try:
        # 1) Create a thread
        thread = client.agents.threads.create()
        thread_id = thread.id

        # 2) Create a user message
        client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        # 3) Create a run
        run = client.agents.runs.create(thread_id=thread_id, agent_id=agent_id)

        # 4) Poll until terminal status or timeout
        terminal_states = {"completed", "failed", "cancelled", "expired"}
        start = time.time()
        while run.status not in terminal_states:
            elapsed_ms = (time.time() - start) * 1000.0
            if elapsed_ms > hard_timeout_ms:
                # Optionally: cancel the run here if supported, then break
                break
            time.sleep(poll_interval_ms / 1000.0)
            run = client.agents.runs.get(thread_id=thread_id, run_id=run.id)

        # 5) List messages (ascending)
        messages_iter = client.agents.messages.list(thread_id=thread_id, order="asc")

        messages: List[Dict[str, Any]] = []
        for m in messages_iter:
            # Extract the newest text item if present
            text_value: Optional[str] = None
            if getattr(m, "text_messages", None):
                # Python SDK often offers `text_messages` convenience
                text_value = m.text_messages[-1].text.value
            else:
                # Fallback for raw content shape
                if getattr(m, "content", None):
                    for c in m.content:
                        if isinstance(c, dict) and c.get("type") == "text" and "text" in c:
                            # c["text"] can be dict with "value"
                            text_obj = c["text"]
                            text_value = text_obj["value"] if isinstance(text_obj, dict) else str(text_obj)
                            break

            messages.append({
                "id": m.id,
                "role": m.role,
                "text": text_value
            })

        result = {
            "threadId": thread_id,
            "run": {
                "id": run.id,
                "status": run.status,
                "lastError": getattr(run, "last_error", None)
            },
            "messages": messages
        }

        # If we timed out before a terminal state, mark it
        elapsed_ms = (time.time() - start) * 1000.0
        if elapsed_ms > hard_timeout_ms and run.status not in terminal_states:
            result["warning"] = f"Timed out after {hard_timeout_ms} ms; last known status={run.status}"

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json",
            headers=_cors_headers()
        )

    except Exception as e:
        # Surface a concise message back to the client
        return _server_error("Agent run failed.", str(e))
