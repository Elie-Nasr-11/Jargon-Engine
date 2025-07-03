import re

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []

    def run(self, code: str):
        self.memory = {}
        self.output_log = []
        self.lines = [line.strip() for line in code.strip().splitlines()]
        self.index = 0
        while self.index < len(self.lines):
            self.execute_line(self.lines[self.index])
            self.index += 1
        return "\n".join(self.output_log)

    def execute_line(self, line: str):
        if not line or line.startswith("#"):
            return

        tokens = line.split()
        cmd = tokens[0]

        if cmd == "SET":
            var = tokens[1]
            expr = " ".join(tokens[2:]).strip("()")
            self.memory[var] = self.safe_eval(expr)

        elif cmd == "PRINT":
            expr = " ".join(tokens[1:]).strip("()\"'")
            self.output_log.append(str(self.safe_eval(expr)))

        elif cmd == "ADD":
            value = self.safe_eval(tokens[1])
            target = tokens[3]
            if isinstance(self.memory[target], list):
                self.memory[target].append(value)
            elif isinstance(self.memory[target], str):
                self.memory[target] += str(value)
            elif isinstance(self.memory[target], set):
                self.memory[target].add(value)
            else:
                raise Exception(f"Cannot ADD to type {type(self.memory[target])}")

        elif cmd == "REMOVE":
            value = self.safe_eval(tokens[1])
            target = tokens[3]
            if isinstance(self.memory[target], list):
                self.memory[target].remove(value)
            elif isinstance(self.memory[target], str):
                self.memory[target] = self.memory[target].replace(str(value), "")
            elif isinstance(self.memory[target], set):
                self.memory[target].discard(value)
            else:
                raise Exception(f"Cannot REMOVE from type {type(self.memory[target])}")

        elif cmd == "REPEAT_UNTIL":
            condition = " ".join(tokens[1:])
            block = self.collect_block()
            while not self.evaluate_condition(condition):
                for sub in block:
                    self.execute_line(sub)

        elif cmd == "REPEAT":
            if "times" in tokens:
                count = int(tokens[1])
                block = self.collect_block()
                for _ in range(count):
                    for sub in block:
                        self.execute_line(sub)

        elif cmd == "IF":
            condition = " ".join(tokens[1:tokens.index("THEN")])
            block = self.collect_block()
            if self.evaluate_condition(condition):
                for sub in block:
                    self.execute_line(sub)

        elif cmd == "BREAK":
            raise Exception("BREAK outside loop")  # only placeholder for future use

        else:
            raise Exception(f"Unknown command: {cmd}")

    def collect_block(self):
        block = []
        self.index += 1
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.strip() == "END":
                break
            block.append(line.strip())
            self.index += 1
        return block

    def safe_eval(self, expr: str):
        expr = expr.replace("is equal to", "==") \
                   .replace("is not equal to", "!=") \
                   .replace("is greater than or equal to", ">=") \
                   .replace("is less than or equal to", "<=") \
                   .replace("is greater than", ">") \
                   .replace("is less than", "<") \
                   .replace("AND", "and") \
                   .replace("OR", "or") \
                   .replace("NOT", "not") \
                   .replace("IS IN", "in")

        for var in sorted(self.memory, key=len, reverse=True):
            expr = expr.replace(var, str(self.memory[var]))
        return eval(expr)

    def evaluate_condition(self, condition: str):
        return bool(self.safe_eval(condition))

code = """

"""

interpreter = StructuredJargonInterpreter()
interpreter.run(code)
print(interpreter.get_output())
