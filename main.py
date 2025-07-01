
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from StructuredJargonInterpreter import StructuredJargonInterpreter

app = FastAPI()

origins = ["*"]  # Adjust CORS origins as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

interpreter = StructuredJargonInterpreter()

@app.post("/run")
async def run_code(req: Request):
    data = await req.json()
    code = data.get("code", "")
    interpreter.run(code)
    return {"output": interpreter.get_output()}
