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

        # Reset interpreter states before a fresh run
        interpreter.resume_context = None
        interpreter.resume_state = None

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
        error_trace = traceback.format_exc()
        print("==== SERVER ERROR (/run) ====")
        print(error_trace)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "trace": error_trace
            }
        )

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

        # Set value and continue
        memory[var] = value
        print(">>> Resuming with:", var, value)
        print(">>> Code snippet:\n", code)
        print(">>> Memory:", memory)

        try:
            result = interpreter.resume(code, memory)
            return {
                "result": result["output"],
                "memory": result["memory"]
            }

        except AskException as ask:
            print(">>> ASK triggered again:", ask.prompt)
            return {
                "ask": ask.prompt,
                "ask_var": ask.variable,
                "result": interpreter.output_log,
                "memory": interpreter.memory
            }

        except Exception as e:
            import traceback
            print(">>> RESUME CRASH >>>")
            print(traceback.format_exc())
            raise

    except Exception as e:
        print("==== SERVER ERROR (/resume outer) ====")
        import traceback
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

    except Exception as e:
        print("==== SERVER ERROR (/resume) ====")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.options("/{rest_of_path:path}", include_in_schema=False)
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=204, content={})
