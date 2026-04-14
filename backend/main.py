import os
import json
import torch
import subprocess
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from .database import init_db
from .routes.auth import router as auth_router
from .routes.admin import router as admin_router
from .agents import orchestrate

# ─────────────────────────────────────────────
#  Globals
# ─────────────────────────────────────────────
model = None
tokenizer = None
MODEL_NAME  = "zai-org/GLM-5"
ENGINE_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "engine")
BUILDER_BIN = os.path.join(ENGINE_DIR, "builder")

# ─────────────────────────────────────────────
#  Lifespan: load GLM-5 on startup
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    # Init database tables
    print("[Antigravity] Initializing database…")
    init_db()
    # Load AI model
    print("[Antigravity] Loading GLM-5 onto GPU…")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        ).eval()
        print("[Antigravity] GLM-5 ready.")
    except Exception as e:
        print(f"[Antigravity] Model load failed (non-GPU env?): {e}")
    yield
    model = None
    tokenizer = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# ─────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────
app = FastAPI(title="Antigravity Builder API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register route modules ────────────────────────
app.include_router(auth_router)
app.include_router(admin_router)

# ─────────────────────────────────────────────
#  Models
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    text: str

class BuildRequest(BaseModel):
    project_name: str = "generated_app"
    type: str = "web"        # "web" | "android"
    files: dict = {}         # { "relative/path.ext": "file content..." }

# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ai_loaded": model is not None,
        "engine_ready": os.path.exists(BUILDER_BIN)
    }

# ─────────────────────────────────────────────
#  Chat → GLM-5 inference
# ─────────────────────────────────────────────
@app.post("/api/chat")
async def process_chat(request: ChatRequest):
    user_input = request.text

    if model is None or tokenizer is None:
        return {
            "reply": (
                f"[Mock GLM-5 Engine]\n\n"
                f"Received prompt: **{user_input}**\n\n"
                "I would generate a full-stack app scaffold here. "
                "Deploy to Colab with a GPU runtime to activate the real GLM-5 model."
            )
        }

    try:
        system_prompt = (
            "You are the Antigravity Builder AI. "
            "Generate full-stack app code from the user's description. "
            "Return a valid JSON object with keys: "
            "project_name (string), type ('web' or 'android'), "
            "files (object mapping relative file paths to their content as strings). "
            "Wrap the JSON in a ```json ... ``` code block."
        )
        messages = [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_input}
        ]
        inputs = tokenizer.apply_chat_template(
            messages, return_tensors="pt", add_generation_prompt=True
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_new_tokens=2048,
                temperature=0.7,
                top_p=0.8,
                repetition_penalty=1.05
            )

        reply_tokens = outputs[0][inputs.shape[-1]:]
        ai_reply = tokenizer.decode(reply_tokens, skip_special_tokens=True)
        return {"reply": ai_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

# ─────────────────────────────────────────────
#  Multi-Agent Chat (Architect → Coder → Reviewer)
# ─────────────────────────────────────────────
@app.post("/api/chat/agents")
async def multi_agent_chat(request: ChatRequest):
    """Run the full multi-agent pipeline for higher quality output."""
    if model is None or tokenizer is None:
        return {
            "reply": "[Multi-Agent Mode] GLM-5 not loaded. Deploy to Colab GPU to use multi-agent pipeline.",
            "pipeline": "architect → coder → reviewer"
        }
    try:
        result = await orchestrate(model, tokenizer, request.text)
        # Return the coder output as the main reply, with review attached
        return {
            "reply": result["code"],
            "review": result["review"],
            "architecture": result["architecture"],
            "pipeline": result["pipeline"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-agent error: {e}")

# ─────────────────────────────────────────────
#  APK Generation (Android builds)
# ─────────────────────────────────────────────
@app.post("/api/build/apk")
async def build_apk(request: BuildRequest):
    """Build an Android APK via the C++ engine with type=android."""
    payload = request.dict()
    payload["type"] = "android"
    return StreamingResponse(
        _stream_builder(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ─────────────────────────────────────────────
#  Build → SSE streaming from C++ engine
# ─────────────────────────────────────────────
async def _stream_builder(payload: dict):
    """Async generator: writes payload.json then streams C++ builder stdout as SSE."""
    payload_path = os.path.join(ENGINE_DIR, "payload.json")
    with open(payload_path, "w") as f:
        json.dump(payload, f)

    # Confirm engine binary exists
    if not os.path.exists(BUILDER_BIN):
        err = json.dumps({"stage": "init", "message": "Builder binary not found. Did setup.sh run?", "level": "error"})
        yield f"data: {err}\n\n"
        return

    proc = await asyncio.create_subprocess_exec(
        BUILDER_BIN, "payload.json",
        cwd=ENGINE_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    async for raw_line in proc.stdout:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if line:
            # The C++ engine already outputs JSON lines
            yield f"data: {line}\n\n"

    await proc.wait()

    # Final artifact URL signal
    artifact = f"output_{payload.get('project_name', 'app')}.zip"
    done_event = json.dumps({
        "stage": "done",
        "message": "Build complete!",
        "level": "success",
        "artifact_url": f"/api/download/{artifact}"
    })
    yield f"data: {done_event}\n\n"

@app.post("/api/build/stream")
async def build_stream(request: BuildRequest):
    payload = request.dict()
    return StreamingResponse(
        _stream_builder(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ─────────────────────────────────────────────
#  Download artifact
# ─────────────────────────────────────────────
@app.get("/api/download/{filename}")
def download(filename: str):
    artifact_path = os.path.join(ENGINE_DIR, filename)
    if not os.path.exists(artifact_path):
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(artifact_path, filename=filename, media_type="application/zip")

# ─────────────────────────────────────────────
#  Serve Vite static build
# ─────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def no_frontend():
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}
