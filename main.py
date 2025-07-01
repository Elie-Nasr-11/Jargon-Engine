from fastapi import FastAPI, Request
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()
interpreter = StructuredJargonInterpreter()

@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    output = interpreter.run(code)
    return {"output": output}
