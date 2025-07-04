from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException
import traceback

app = FastAPI()
interpreter = StructuredJargonInterpreter()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Backend is live"}

@app.post("/run")
async def run_code(req: Request):
    try:
        data = await req.json()
        code = data.get("code", "")
        memory = data.get("memory", {})

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

    except Exception as e:
        print("==== SERVER ERROR (/run) ====")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/resume")
async def resume_code(req: Request):
    try:
        data = await req.json()
        var = data.get("var")
        value = data.get("value")
        code = data.get("code", "")
        memory = data.get("memory", {})

        # Set value in memory and resume
        memory[var] = value
        result = interpreter.resume(code, memory)

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

    except Exception as e:
        print("==== SERVER ERROR (/resume) ====")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
