from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException

app = FastAPI()
interpreter = StructuredJargonInterpreter()

# ✅ Enable CORS for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #https://jargoninterpreter.netlify.app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check route
@app.get("/")
async def root():
    return {"message": "Backend is live"}

# ✅ POST /run route
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

# ✅ Handle OPTIONS /run
@app.options("/run", include_in_schema=False)
async def run_options():
    return JSONResponse(content={}, status_code=204)

# ✅ POST /resume route
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

# ✅ Handle OPTIONS /resume
@app.options("/resume", include_in_schema=False)
async def resume_options():
    return JSONResponse(content={}, status_code=204)

# ✅ Global fallback for unmatched OPTIONS (just in case)
@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
