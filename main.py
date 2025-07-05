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
    allow_origins=["*"],  # Replace in production
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

        interpreter = StructuredJargonInterpreter()  # create new instance
        result = interpreter.run(code, memory)

        if interpreter.pending_ask:
            return {
                "ask": interpreter.pending_ask.prompt,
                "ask_var": interpreter.pending_ask.variable,
                "result": result["output"],
                "memory": result["memory"]
            }

        return {
            "result": result["output"],
            "memory": result["memory"]
        }

    except Exception as e:
        print("==== SERVER ERROR (/run) ====")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )

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

        print(">>> Resuming with:", var, value)
        print(">>> Code snippet:\n", code)
        print(">>> Memory:", memory)

        interpreter = StructuredJargonInterpreter()  # new instance here too
        result = interpreter.resume(code, memory)

        if interpreter.pending_ask:
            return {
                "ask": interpreter.pending_ask.prompt,
                "ask_var": interpreter.pending_ask.variable,
                "result": result["output"],
                "memory": result["memory"]
            }

        return {
            "result": result["output"],
            "memory": result["memory"]
        }

    except Exception as e:
        print("==== SERVER ERROR (/resume) ====")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
        
@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
