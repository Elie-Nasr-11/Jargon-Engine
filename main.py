from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()
interpreter = StructuredJargonInterpreter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run")
async def run_code(req: Request):
    data = await req.json()
    code = data["input"]
    result, ask_prompt = interpreter.run(code)
    return {"result": result, "ask": ask_prompt}

@app.post("/answer")
async def handle_answer(req: Request):
    data = await req.json()
    answer = data["answer"]
    result, ask_prompt = interpreter.resume(answer)
    return {"result": result, "ask": ask_prompt}
