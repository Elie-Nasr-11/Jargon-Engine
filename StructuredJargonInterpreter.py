import re

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_block = None
        self.pending_index = 0
        self.pending_var = None
        self.max_steps = 1000
        self.break_loop = False

    def run(self, code: str):
        self.memory.clear()
        self.output_log.clear()
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_block = None
        self.pending_index = 0
        self.pending_var = None
        self.break_loop = False

        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.execute_block(self.lines)

    def execute_block(self, block, start=0):
        i = start
        steps = 0
        while i < len(block):
            if self.awaiting_input:
                self.pending_block = block
                self.pending_index = i
                return
            line = block[i]
            steps += 1
            if steps > self.max_steps:
                self.output_log.append("[ERROR] Execution stopped: Too many steps.")
                return
            if line == "BREAK":
                self.break_loop = True
                return
            if line.startswith("SET "):
                self.handle_set(line)
            elif line.startswith("PRINT "):
                self.handle_print(line)
            elif line.startswith("ASK "):
                if self.handle_ask(line):
                    return
            elif line.startswith("IF "):
                sub, jump = self.collect_block(block, i, "END")
                self.handle_if_else(sub)
                i = jump - 1
            elif line.startswith("REPEAT_UNTIL"):
                sub, jump = self.collect_block(block, i, "END")
                self.handle_repeat_until(sub)
                i = jump - 1
            else:
                self.output_log.append(f"[ERROR] Unknown command: {line}")
            i += 1

    def collect_block(self, lines, start, end_kw):
        block = [lines[start]]
        i = start + 1
        nest = 1
        while i < len(lines):
            line = lines[i]
            if any(line.startswith(k) for k in ["IF ", "REPEAT_UNTIL"]):
                nest += 1
            elif line == end_kw:
                nest -= 1
                if nest == 0:
                    block.append(line)
                    break
            block.append(line)
            i += 1
        return block, i + 1

    def resume(self, user_input: str):
        if self.pending_var:
            self.memory[self.pending_var] = user_input
            self.awaiting_input = False
            self.ask_prompt = ""
            self.pending_var = None
            if self.pending_block is not None:
                self.execute_block(self.pending_block, self.pending_index)
        else:
            self.output_log.append("[ERROR] No pending variable to assign input to.")

    def handle_ask(self, line):
        match = re.match(r'ASK\s+"(.+?)"\s+as\s+(\w+)', line)
        if not match:
            self.output_log.append(f"[ERROR] Invalid ASK syntax: {line}")
            return False
        prompt, var = match.groups()
        self.ask_prompt = prompt
        self.awaiting_input = True
        self.pending_var = var
        return True

    def handle_set(self, line):
        match = re.match(r'SET\s+(\w+)\s*\((.+)\)', line)
        if not match:
            self.output_log.append(f"[ERROR] Invalid SET syntax: {line}")
            return
        var, expr = match.groups()
        value = self.safe_eval(expr)
        self.memory[var] = value

    def handle_print(self, line):
        expr = line[6:].strip()
        val = self.safe_eval(expr)
        self.output_log.append(str(val))

    def handle_if_else(self, block):
        cond = block[0].replace("IF", "").replace("THEN", "").strip()
        true_block = []
        false_block = []
        curr = true_block
        i = 1
        nest = 0
        while i < len(block) - 1:
            line = block[i]
            if line == "ELSE" and nest == 0:
                curr = false_block
                i += 1
                continue
            if line.startswith("IF "):
                nest += 1
            elif line == "END":
                if nest > 0:
                    nest -= 1
            curr.append(line)
            i += 1
        if self.evaluate_condition(cond):
            self.execute_block(true_block)
        else:
            self.execute_block(false_block)

    def handle_repeat_until(self, block):
        condition = block[0].replace("REPEAT_UNTIL", "").strip()
        count = 0
        while not self.evaluate_condition(condition):
            self.break_loop = False
            self.execute_block(block[1:-1])
            if self.awaiting_input:
                self.pending_block = block
                self.pending_index = 0  # re-evaluate condition after resume
                return
            if self.break_loop:
                break
            count += 1
            if count > self.max_steps:
                self.output_log.append("[ERROR] Loop exceeded max iterations.")
                break

    def safe_eval(self, expr):
        expr = expr.strip()
        try:
            tokens = re.findall(r'\b\w+\b', expr)
            for token in tokens:
                if token in self.memory:
                    val = self.memory[token]
                    if isinstance(val, str):
                        expr = re.sub(rf'\b{token}\b', f'"{val}"', expr)
                    else:
                        expr = re.sub(rf'\b{token}\b', str(val), expr)
            return eval(expr, {"__builtins__": None}, {})
        except Exception as e:
            self.output_log.append(f"[ERROR] Eval failed: {e} — in ({expr})")
            return None

    def evaluate_condition(self, text: str) -> bool:
        try:
            if "AND" in text:
                parts = text.split("AND")
                return all(self.evaluate_condition(p.strip()) for p in parts)
            elif "OR" in text:
                parts = text.split("OR")
                return any(self.evaluate_condition(p.strip()) for p in parts)

            ops = [
                ("is equal to", "=="),
                ("is not equal to", "!="),
                ("is greater than or equal to", ">="),
                ("is less than or equal to", "<="),
                ("is greater than", ">"),
                ("is less than", "<")
            ]
            for phrase, op in ops:
                if phrase in text:
                    a, b = text.split(phrase)
                    return self.safe_eval(f"({a.strip()}) {op} ({b.strip()})")

            if "is even" in text:
                expr = text.split("is even")[0].strip()
                return self.safe_eval(expr) % 2 == 0
            if "is odd" in text:
                expr = text.split("is odd")[0].strip()
                return self.safe_eval(expr) % 2 == 1
            return bool(self.safe_eval(text))
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition eval failed: {e} — in ({text})")
            return False

    def get_output(self):
        return "\n".join(str(x) for x in self.output_log)

    def provide_answer(self, user_input: str):
        if not self.awaiting_input:
            return None
        self.resume(user_input)
        return self.get_output()

code = """

"""

interpreter = StructuredJargonInterpreter()
interpreter.run(code)
print(interpreter.get_output())
