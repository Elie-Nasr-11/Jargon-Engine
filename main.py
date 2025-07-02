from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    interpreter = StructuredJargonInterpreter()
    interpreter.run(code)
    if interpreter.ask_state:
        return { "ask": interpreter.ask_state }
    output = interpreter.get_output()
    return { "output": output }
