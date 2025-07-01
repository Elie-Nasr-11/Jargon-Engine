from fastapi import FastAPI, Request
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()
interpreter = StructuredJargonInterpreter()

@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    interpreter.run(code)
    return {"output": interpreter.get_output()}
