from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException
import traceback

app = FastAPI()
interpreter = StructuredJargonInterpreter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Jargon Backend is live"}

@app.post("/run")
async def run_code(req: Request):
    try:
        data = await req.json()
        code = data.get("code", "")
        memory = data.get("memory", {})

        result = interpreter.run(code, memory)

        response = {
            "result": result["output"] or ["[No output returned]"],
            "memory": result["memory"]
        }

        if interpreter.pending_ask:
            response.update({
                "ask": interpreter.pending_ask.prompt,
                "ask_var": interpreter.pending_ask.variable,
            })

        return response

    except Exception as e:
        print("==== SERVER ERROR (/run) ====")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/resume")
async def resume_code(req: Request):
    try:
        data = await req.json()
        code = data.get("code", "")
        memory = data.get("memory", {})
        var = data.get("var")
        value = data.get("value")

        if var:
            memory[var] = value

        result = interpreter.resume(code, memory)

        response = {
            "result": result["output"] or ["[No output returned]"],
            "memory": result["memory"]
        }

        if interpreter.pending_ask:
            response.update({
                "ask": interpreter.pending_ask.prompt,
                "ask_var": interpreter.pending_ask.variable,
            })

        return response

    except Exception as e:
        print("==== SERVER ERROR (/resume) ====")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
