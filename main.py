from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()
interpreter = StructuredJargonInterpreter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run")
async def run_code(req: Request):
    data = await req.json()
    code = data.get("input", "")
    interpreter.run(code)
    return {"result": interpreter.get_output()}
