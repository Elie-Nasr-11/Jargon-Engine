from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException

app = FastAPI()
interpreter = StructuredJargonInterpreter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            "result": interpreter.output_log,  # This can stay as-is
            "memory": interpreter.memory        # So frontend continues state
        }
