class AskException(Exception):
    def __init__(self, prompt: str, variable: str):
        self.prompt = prompt
        self.variable = variable
        super().__init__(f"ASK triggered: {prompt} → {variable}")
