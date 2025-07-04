from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException

app = FastAPI()
interpreter = StructuredJargonInterpreter()

# ✅ CORSMiddleware must come before any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jargoninterpreter.netlify.app"],  # No trailing slash
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check
@app.get("/")
async def root():
    return {"message": "Backend is live"}

# ✅ Main code route
@app.post("/run")
async def run_code(req: Request):
    data = await req.json()
    code = data.get("code", "")
    memory = data.get("memory", {})

    try:
        result = interpreter.run(code, memory)
        return {
            "result": result["output"],
            "memory": result["memory"]
        }
    except AskException as ask:
        return {
            "ask": ask.prompt,
            "ask_var": ask.variable,
            "result": interpreter.output_log,
            "memory": interpreter.memory
        }

# ✅ Resume route
@app.post("/resume")
async def resume_code(req: Request):
    data = await req.json()
    var = data.get("var")
    value = data.get("value")

    interpreter.memory[var] = value
    interpreter.pending_ask = None

    try:
        result = interpreter.run(interpreter.code, interpreter.memory)
        return {
            "result": result["output"],
            "memory": result["memory"]
        }
    except AskException as ask:
        return {
            "ask": ask.prompt,
            "ask_var": ask.variable,
            "result": interpreter.output_log,
            "memory": interpreter.memory
        }

# ✅ CORS preflight fallback for all unmatched OPTIONS
@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
