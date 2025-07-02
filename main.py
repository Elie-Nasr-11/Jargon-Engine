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
async def run_code(request: Request):
    data = await request.json()
    code = data.get("input", "")
    interpreter.run(code)
    output = interpreter.get_output()
    if interpreter.awaiting_input:
        return {"ask": interpreter.ask_prompt}
    return {"result": output}

@app.post("/answer")
async def answer_question(request: Request):
    data = await request.json()
    user_answer = data.get("answer", "")
    output = interpreter.provide_answer(user_answer)
    return {"result": output} if output else {"ask": interpreter.ask_prompt}

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
