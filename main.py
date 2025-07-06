from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from StructuredJargonInterpreter import StructuredJargonInterpreter
import traceback

app = FastAPI()

# Allow all origins for development (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Jargon Backend is live."}

@app.post("/run")
async def run_code(req: Request):
    try:
        data = await req.json()
        code = data.get("code", "")
        answers = data.get("answers", [])

        interpreter = StructuredJargonInterpreter()

        # Internal answer index tracking
        interpreter.answers = answers
        interpreter.answer_index = 0

        # Run code
        interpreter.run(code)

        response = {
            "result": interpreter.output_log or ["[No output returned]"],
            "memory": interpreter.memory,
        }

        if interpreter.pending_question:
            response.update({
                "ask": interpreter.pending_question["prompt"],
                "ask_var": interpreter.pending_question["variable"],
            })

        return response

    except Exception as e:
        print("==== SERVER ERROR (/run) ====")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
