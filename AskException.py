class AskException(Exception):
    def __init__(self, prompt, variable):
        self.prompt = prompt
        self.variable = variable
