import re

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.max_steps = 1000
        self.break_loop = False
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_block = None  # can be a function or list
        self.pending_index = 0
        self.pending_stack = []

    def run(self, code: str):
        self.__init__()  # reset everything
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.execute_block(self.lines)

    def resume(self, user_input: str):
        if not self.pending_stack:
            self.output_log.append("[ERROR] No variable to assign input to.")
            return
        var = self.pending_stack.pop()
        self.memory[var] = user_input
        self.awaiting_input = False
        self.ask_prompt = ""
        if callable(self.pending_block):
            self.pending_block()
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
            steps += 1
            if steps > self.max_steps:
                self.output_log.append("[ERROR] Execution stopped: Too many steps (possible infinite loop).")
                break
            if self.break_loop:
                break
            line = block[i]
            if line == "BREAK":
                self.break_loop = True
                break
            elif line.startswith("SET "): self.handle_set(line)
            elif line.startswith("PRINT "): self.handle_print(line)
            elif line.startswith("ADD "): self.handle_add(line)
            elif line.startswith("REMOVE "): self.handle_remove(line)
            elif line.startswith("ASK "):
                if self.handle_ask(line): return
            elif line.startswith("IF "):
                sub_block, jump = self.collect_block(block, i, "END")
                self.handle_if_else(sub_block)
                i = jump - 1
            elif line.startswith("REPEAT_UNTIL"):
                sub_block, jump = self.collect_block(block, i, "END")
                self.handle_repeat_until(sub_block)
                i = jump - 1
            elif line.startswith("REPEAT "):
                sub_block, jump = self.collect_block(block, i, "END")
                self.handle_repeat_n_times(sub_block)
                i = jump - 1
            elif line.startswith("REPEAT_FOR_EACH"):
                sub_block, jump = self.collect_block(block, i, "END")
                self.handle_repeat_for_each(sub_block)
                i = jump - 1
            else:
                self.output_log.append(f"[ERROR] Unknown command: {line}")
            i += 1

    def collect_block(self, lines, start, end_keyword):
        block = [lines[start]]
        i = start + 1
        nested = 1
        while i < len(lines):
            line = lines[i]
            if any(line.startswith(k) for k in ["IF ", "REPEAT_UNTIL", "REPEAT ", "REPEAT_FOR_EACH"]):
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
        m_idx = re.match(r'SET\s+(\w+)\[(.+?)\]\s*\((.+)\)', line)
        m_simple = re.match(r'SET\s+(\w+)\s*\((.+)\)', line)
        if m_idx:
            var, i_expr, v_expr = m_idx.groups()
            i = self.safe_eval(i_expr)
            v = self.safe_eval(v_expr)
            if var in self.memory and isinstance(self.memory[var], list):
                try: self.memory[var][i] = v
                except: self.output_log.append(f"[ERROR] Failed to assign {var}[{i}]")
            else: self.output_log.append(f"[ERROR] {var} is not a list")
        elif m_simple:
            var, expr = m_simple.groups()
            self.memory[var] = self.safe_eval(expr)
        else:
            self.output_log.append(f"[ERROR] Invalid SET syntax: {line}")

    def handle_print(self, line):
        expr = line[6:].strip()
        val = self.safe_eval(expr)
        self.output_log.append(str(val))

    def handle_add(self, line):
        m = re.match(r'ADD\s+(.+?)\s+to\s+(\w+)', line)
        if not m:
            self.output_log.append(f"[ERROR] Invalid ADD syntax: {line}")
            return
        v_expr, lst = m.groups()
        v = self.safe_eval(v_expr)
        if lst not in self.memory or not isinstance(self.memory[lst], list):
            self.memory[lst] = []
        self.memory[lst].append(v)

    def handle_remove(self, line):
        m = re.match(r'REMOVE\s+(.+?)\s+from\s+(\w+)', line)
        if not m:
            self.output_log.append(f"[ERROR] Invalid REMOVE syntax: {line}")
            return
        v_expr, lst = m.groups()
        v = self.safe_eval(v_expr)
        if lst in self.memory and isinstance(self.memory[lst], list):
            try: self.memory[lst].remove(v)
            except ValueError: self.output_log.append(f"[ERROR] Value {v} not found in {lst}")
        else:
            self.output_log.append(f"[ERROR] {lst} is not a list or not defined")

    def handle_ask(self, line):
        m = re.match(r'ASK\s+"(.+?)"\s+as\s+(\w+)', line)
        if not m:
            self.output_log.append(f"[ERROR] Invalid ASK syntax: {line}")
            return False
        self.ask_prompt, var = m.groups()
        self.awaiting_input = True
        self.pending_stack.append(var)
        return True

    def handle_if_else(self, block):
        cond = block[0].replace("IF", "").replace("THEN", "").strip()
        true_block, false_block, current, i, nest = [], [], True, 1, 0
        while i < len(block) - 1:
            line = block[i]
            if line == "ELSE" and nest == 0:
                current = False
                i += 1
                continue
            if line.startswith("IF "): nest += 1
            elif line == "END" and nest > 0: nest -= 1
            (true_block if current else false_block).append(line)
            i += 1
        self.execute_block(true_block if self.evaluate_condition(cond) else false_block)

    def handle_repeat_until(self, block):
        cond = block[0].replace("REPEAT_UNTIL", "").strip()
        def loop():
            while not self.evaluate_condition(cond):
                self.break_loop = False
                self.execute_block(block[1:-1])
                if self.awaiting_input:
                    self.pending_block = loop
                    return
                if self.break_loop: break
        loop()

    def handle_repeat_n_times(self, block):
        match = re.match(r'REPEAT\s+(\d+)\s+times', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT syntax: {block[0]}")
            return
        times, count = int(match.group(1)), 0
        def loop():
            nonlocal count
            while count < times:
                self.break_loop = False
                self.execute_block(block[1:-1])
                if self.awaiting_input:
                    self.pending_block = loop
                    return
                if self.break_loop: break
                count += 1
        loop()

    def handle_repeat_for_each(self, block):
        match = re.match(r'REPEAT_FOR_EACH\s+(\w+)\s+in\s+(\w+)', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT_FOR_EACH syntax: {block[0]}")
            return
        var, lst = match.groups()
        values = self.memory.get(lst, [])
        idx = 0
        def loop():
            nonlocal idx
            while idx < len(values):
                self.memory[var] = values[idx]
                self.break_loop = False
                self.execute_block(block[1:-1])
                if self.awaiting_input:
                    self.pending_block = loop
                    return
                if self.break_loop: break
                idx += 1
        loop()

    def safe_eval(self, expr):
        expr = expr.strip()
        try:
            if expr in self.memory:
                return self.memory[expr]
    
            tokens = re.findall(r'\b\w+\b', expr)
            for token in tokens:
                if token in self.memory and isinstance(self.memory[token], str):
                    expr = re.sub(rf'\b{token}\b', f'"{self.memory[token]}"', expr)
            code = compile(expr, "<string>", "eval")
            return eval(code, {"__builtins__": None}, {
                "int": int, "abs": abs, "min": min, "max": max,
                "float": float, "round": round, "list": list, "str": str, "bool": bool,
                **self.memory
            })
        except Exception as e:
            self.output_log.append(f"[ERROR] Eval failed: {e} — in ({expr})")
            return expr if isinstance(expr, str) else None

    def evaluate_condition(self, text: str) -> bool:
        try:
            if "AND" in text:
                return all(self.evaluate_condition(p.strip()) for p in text.split("AND"))
            if "OR" in text:
                return any(self.evaluate_condition(p.strip()) for p in text.split("OR"))
            for phrase, sym in [("is equal to", "=="), ("is not equal to", "!="),
                                ("is greater than or equal to", ">="), ("is less than or equal to", "<="),
                                ("is greater than", ">"), ("is less than", "<"), ("is in", "in")]:
                if phrase in text:
                    a, b = text.split(phrase)
                    return self.safe_eval(f"({a.strip()}) {sym} ({b.strip()})")
            if "is even" in text:
                return self.safe_eval(text.split("is even")[0].strip()) % 2 == 0
            if "is odd" in text:
                return self.safe_eval(text.split("is odd")[0].strip()) % 2 == 1
            if "reaches end of" in text:
                a, b = text.split("reaches end of")
                return self.safe_eval(a.strip()) >= len(self.safe_eval(b.strip()))
            self.output_log.append(f"[ERROR] Unrecognized condition: {text}")
            return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition evaluation failed: {e} — in ({text})")
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
