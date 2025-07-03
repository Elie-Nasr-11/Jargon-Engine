import re

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.max_steps = 1000
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_stack = []
        self.pending_block = None
        self.pending_index = 0
        self.resume_loop_type = None  # "REPEAT_UNTIL", "REPEAT", etc.

    def run(self, code: str):
        self.__init__()  # reset all state
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.execute_block(self.lines)

    def resume(self, user_input: str):
        if not self.awaiting_input:
            self.output_log.append("[ERROR] Not awaiting input.")
            return
        if not self.pending_stack or self.pending_block is None:
            self.output_log.append("[ERROR] No pending block to resume.")
            return

        self.awaiting_input = False
        self.ask_prompt = ""
        var = self.pending_stack.pop()
        self.memory[var] = str(user_input)

        if self.resume_loop_type == "REPEAT_UNTIL":
            self.handle_repeat_until(self.pending_block)
        else:
            self.execute_block(self.pending_block, self.pending_index)

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
                break
            if line == "BREAK":
                break
            if line.startswith("SET "):
                self.handle_set(line)
            elif line.startswith("PRINT "):
                self.handle_print(line)
            elif line.startswith("ASK "):
                if self.handle_ask(line):
                    return
            elif line.startswith("IF "):
                sub_block, jump_to = self.collect_block(block, i, "END")
                self.handle_if_else(sub_block)
                i = jump_to - 1
            elif line.startswith("REPEAT_UNTIL"):
                sub_block, jump_to = self.collect_block(block, i, "END")
                self.handle_repeat_until(sub_block)
                i = jump_to - 1
            else:
                self.output_log.append(f"[ERROR] Unknown command: {line}")
            i += 1

    def collect_block(self, lines, start, end_keyword):
        block = [lines[start]]
        i = start + 1
        nested = 1
        while i < len(lines):
            line = lines[i]
            if line.startswith(("IF ", "REPEAT_UNTIL")):
                nested += 1
            elif line == end_keyword:
                nested -= 1
                if nested == 0:
                    block.append(line)
                    break
            block.append(line)
            i += 1
        return block, i + 1

    def handle_set(self, line):
        match = re.match(r'SET\s+(\w+)\s*\((.+)\)', line)
        if match:
            var, expr = match.groups()
            self.memory[var] = self.safe_eval(expr)
        else:
            self.output_log.append(f"[ERROR] Invalid SET syntax: {line}")

    def handle_print(self, line):
        expr = line[6:].strip()
        val = self.safe_eval(expr)
        self.output_log.append(str(val))

    def handle_ask(self, line):
        match = re.match(r'ASK\s+"(.+?)"\s+as\s+(\w+)', line)
        if not match:
            self.output_log.append(f"[ERROR] Invalid ASK syntax: {line}")
            return False
        self.ask_prompt, var = match.groups()
        self.awaiting_input = True
        self.pending_stack.append(var)
        return True

    def handle_if_else(self, block):
        condition_line = block[0]
        condition = condition_line.replace("IF", "").replace("THEN", "").strip()
        true_block = []
        false_block = []
        current_block = true_block
        i = 1
        while i < len(block) - 1:
            line = block[i]
            if line == "ELSE":
                current_block = false_block
            else:
                current_block.append(line)
            i += 1
        if self.evaluate_condition(condition):
            self.execute_block(true_block)
        else:
            self.execute_block(false_block)

    def handle_repeat_until(self, block):
        condition_line = block[0].replace("REPEAT_UNTIL", "").strip()
        self.resume_loop_type = "REPEAT_UNTIL"
        count = 0
        while not self.evaluate_condition(condition_line):
            self.execute_block(block[1:-1])
            if self.awaiting_input:
                self.pending_block = block
                return
            count += 1
            if count > self.max_steps:
                self.output_log.append("[ERROR] Loop exceeded max iterations.")
                break
        self.resume_loop_type = None

    def safe_eval(self, expr):
        expr = expr.strip()
        try:
            for key in sorted(self.memory.keys(), key=len, reverse=True):
                val = self.memory[key]
                if isinstance(val, str):
                    expr = re.sub(rf'\b{key}\b', f'"{val}"', expr)
                else:
                    expr = re.sub(rf'\b{key}\b', str(val), expr)
            return eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            self.output_log.append(f"[ERROR] Eval failed: {e} — in ({expr})")
            return None

    def evaluate_condition(self, text: str) -> bool:
        try:
            ops = [
                ("is equal to", "=="), ("is not equal to", "!="),
                ("is greater than or equal to", ">="), ("is less than or equal to", "<="),
                ("is greater than", ">"), ("is less than", "<")
            ]
            for phrase, symbol in ops:
                if phrase in text:
                    a, b = text.split(phrase)
                    return eval(f"{self.safe_eval(a.strip())} {symbol} {self.safe_eval(b.strip())}")
            return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition failed: {e} — in ({text})")
            return False

    def get_output(self):
        return '\n'.join(str(x) for x in self.output_log)

    def provide_answer(self, user_input: str):
        self.resume(user_input)
        return self.get_output()

code = """

"""

interpreter = StructuredJargonInterpreter()
interpreter.run(code)
print(interpreter.get_output())
