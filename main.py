from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter
import os
import uvicorn

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
    try:
        print("Received /run request")
        data = await request.json()
        code = data.get("input", "")
        interpreter.run(code)
        output = interpreter.get_output()
        if hasattr(interpreter, 'awaiting_input') and interpreter.awaiting_input:
            return {"ask": interpreter.ask_prompt}
        return {"result": output}
    except Exception as e:
        print(f"[ERROR] in /run: {e}")
        return {"result": f"[ERROR] Backend crashed: {str(e)}"}

@app.post("/answer")
async def answer_question(request: Request):
    try:
        print("Received /answer request")
        data = await request.json()
        user_answer = data.get("answer", "")
        if hasattr(interpreter, 'provide_answer'):
            output = interpreter.provide_answer(user_answer)
            if output:
                return {"result": output}
            else:
                return {"ask": interpreter.ask_prompt}
        else:
            return {"result": "[ERROR] Input handling not available."}
    except Exception as e:
        print(f"[ERROR] in /answer: {e}")
        return {"result": f"[ERROR] Backend crashed: {str(e)}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
