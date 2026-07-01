"""run.py — CleanSlate AI custom server.

Starts ADK's FastAPI app on port 8000 with:
  - CORS open to all origins (so the /chat page works from the same port)
  - A /chat route that serves launcher.html (the custom welcome UI)

Usage:
    python run.py
    Then open http://127.0.0.1:8000/chat
"""

import pathlib
import uvicorn
from fastapi.responses import HTMLResponse
from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = str(pathlib.Path(__file__).parent / "agents")
LAUNCHER   = pathlib.Path(__file__).parent / "launcher.html"

# Build the ADK FastAPI app with CORS enabled
fast_app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    allow_origins=["*"],
    web=True,
)

# Mount the custom chat UI at /chat
@fast_app.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui():
    return HTMLResponse(content=LAUNCHER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print("CleanSlate AI starting...")
    print("  Custom chat UI  ->  run `python launcher_server.py` (port 8000)")
    print("  ADK dev UI      ->  http://127.0.0.1:8080/dev-ui/")
    uvicorn.run(fast_app, host="127.0.0.1", port=8080)
