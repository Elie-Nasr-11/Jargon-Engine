from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
from AskException import AskException
import traceback

app = FastAPI()
interpreter = StructuredJargonInterpreter()

# ✅ CORS for frontend (change "*" to your domain for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with "https://jargoninterpreter.netlify.app" in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check route
@app.get("/")
async def root():
    return {"message": "Backend is live"}

# ✅ POST /run
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
        print("==== SERVER ERROR ====")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ✅ OPTIONS /run
@app.options("/run", include_in_schema=False)
async def run_options():
    return JSONResponse(content={}, status_code=204)

# ✅ POST /resume
@app.post("/resume")
async def resume_code(req: Request):
    try:
        data = await req.json()
        var = data.get("var")
        value = data.get("value")
        code = data.get("code", "")  # Add this
        memory = data.get("memory", {})

        interpreter.memory[var] = value
        interpreter.pending_ask = None

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
        print("==== SERVER ERROR ====")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ✅ OPTIONS /resume
@app.options("/resume", include_in_schema=False)
async def resume_options():
    return JSONResponse(content={}, status_code=204)

# ✅ Fallback OPTIONS for any route
@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
