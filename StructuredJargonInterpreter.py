import re

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.max_steps = 1000
        self.break_loop = False
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_block = None
        self.pending_index = 0
        self.pending_stack = []

    def run(self, code: str):
        self.memory.clear()
        self.output_log.clear()
        self.break_loop = False
        self.awaiting_input = False
        self.ask_prompt = ""
        self.pending_block = None
        self.pending_index = 0
        self.pending_stack = []

        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.execute_block(self.lines)

    def resume(self, user_input: str):
        self.awaiting_input = False
        self.ask_prompt = ""
        self.memory[self.pending_stack[-1]] = user_input
        if self.pending_index == -999:
            first_line = self.pending_block[0]
            if first_line.startswith("REPEAT_UNTIL"):
                self.handle_repeat_until(self.pending_block)
            elif first_line.startswith("REPEAT "):
                self.handle_repeat_n_times(self.pending_block)
            elif first_line.startswith("REPEAT_FOR_EACH"):
                self.handle_repeat_for_each(self.pending_block)
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
                self.output_log.append("[ERROR] Execution stopped: Too many steps (possible infinite loop).")
                break
            if self.break_loop:
                break
            if line == "BREAK":
                self.break_loop = True
                break
            if line.startswith("SET "):
                self.handle_set(line)
            elif line.startswith("PRINT "):
                self.handle_print(line)
            elif line.startswith("ADD "):
                self.handle_add(line)
            elif line.startswith("REMOVE "):
                self.handle_remove(line)
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
            elif line.startswith("REPEAT "):
                sub_block, jump_to = self.collect_block(block, i, "END")
                self.handle_repeat_n_times(sub_block)
                i = jump_to - 1
            elif line.startswith("REPEAT_FOR_EACH"):
                sub_block, jump_to = self.collect_block(block, i, "END")
                self.handle_repeat_for_each(sub_block)
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
        match_indexed = re.match(r'SET\s+(\w+)\[(.+?)\]\s*\((.+)\)', line)
        match_simple = re.match(r'SET\s+(\w+)\s*\((.+)\)', line)
        if match_indexed:
            var, index_expr, value_expr = match_indexed.groups()
            index = self.safe_eval(index_expr)
            value = self.safe_eval(value_expr)
            if var in self.memory and isinstance(self.memory[var], list):
                try:
                    self.memory[var][index] = value
                except Exception:
                    self.output_log.append(f"[ERROR] Failed to assign {var}[{index}]")
            else:
                self.output_log.append(f"[ERROR] {var} is not a list")
        elif match_simple:
            var, expr = match_simple.groups()
            value = self.safe_eval(expr)
            self.memory[var] = value
        else:
            self.output_log.append(f"[ERROR] Invalid SET syntax: {line}")

    def handle_print(self, line):
        expr = line[6:].strip()
        val = self.safe_eval(expr)
        self.output_log.append(str(val))

    def handle_add(self, line):
        match = re.match(r'ADD\s+(.+?)\s+to\s+(\w+)', line)
        if not match:
            self.output_log.append(f"[ERROR] Invalid ADD syntax: {line}")
            return
        value_expr, list_name = match.groups()
        value = self.safe_eval(value_expr)
        if list_name not in self.memory or not isinstance(self.memory[list_name], list):
            self.memory[list_name] = []
        self.memory[list_name].append(value)

    def handle_remove(self, line):
        match = re.match(r'REMOVE\s+(.+?)\s+from\s+(\w+)', line)
        if not match:
            self.output_log.append(f"[ERROR] Invalid REMOVE syntax: {line}")
            return
        value_expr, list_name = match.groups()
        value = self.safe_eval(value_expr)
        if list_name in self.memory and isinstance(self.memory[list_name], list):
            try:
                self.memory[list_name].remove(value)
            except ValueError:
                self.output_log.append(f"[ERROR] Value {value} not found in {list_name}")
        else:
            self.output_log.append(f"[ERROR] {list_name} is not a list or not defined")

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
        nested = 0
        while i < len(block) - 1:
            line = block[i]
            if line == "ELSE" and nested == 0:
                current_block = false_block
                i += 1
                continue
            if line.startswith("IF "):
                nested += 1
            elif line == "END":
                if nested > 0:
                    nested -= 1
            current_block.append(line)
            i += 1
        if self.evaluate_condition(condition):
            self.execute_block(true_block)
        else:
            self.execute_block(false_block)

    def handle_repeat_until(self, block):
        condition_line = block[0].replace("REPEAT_UNTIL", "").strip()
        count = 0
        while not self.evaluate_condition(condition_line):
            self.break_loop = False
            self.execute_block(block[1:-1])
            if self.awaiting_input:
                self.pending_block = block
                self.pending_index = -999
                return
            if self.break_loop:
                break
            count += 1
            if count > self.max_steps:
                self.output_log.append("[ERROR] Loop exceeded max iterations.")
                break

    def handle_repeat_n_times(self, block):
        match = re.match(r'REPEAT\s+(\d+)\s+times', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT syntax: {block[0]}")
            return
        times = int(match.group(1))
        for _ in range(times):
            self.break_loop = False
            self.execute_block(block[1:-1])
            if self.awaiting_input:
                self.pending_block = block
                self.pending_index = -999
                return
            if self.break_loop:
                break

    def handle_repeat_for_each(self, block):
        match = re.match(r'REPEAT_FOR_EACH\s+(\w+)\s+in\s+(\w+)', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT_FOR_EACH syntax: {block[0]}")
            return
        var, iterable = match.groups()
        for item in self.memory.get(iterable, []):
            self.memory[var] = item
            self.break_loop = False
            self.execute_block(block[1:-1])
            if self.awaiting_input:
                self.pending_block = block
                self.pending_index = -999
                return
            if self.break_loop:
                break

    def safe_eval(self, expr):
    expr = expr.strip()
    try:
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
        return None

    def evaluate_condition(self, text: str) -> bool:
        try:
            if "AND" in text:
                parts = text.split("AND")
                return all(self.evaluate_condition(p.strip()) for p in parts)
            elif "OR" in text:
                parts = text.split("OR")
                return any(self.evaluate_condition(p.strip()) for p in parts)
    
            replacements = [
                ("is equal to", "=="),
                ("is not equal to", "!="),
                ("is greater than or equal to", ">="),
                ("is less than or equal to", "<="),
                ("is greater than", ">"),
                ("is less than", "<"),
                ("is in", "in")
            ]
    
            for phrase, symbol in replacements:
                if phrase in text:
                    a, b = text.split(phrase)
                    return self.safe_eval(f"({a.strip()}) {symbol} ({b.strip()})")
    
            if "is even" in text:
                expr = text.split("is even")[0].strip()
                return self.safe_eval(f"({expr})") % 2 == 0
            if "is odd" in text:
                expr = text.split("is odd")[0].strip()
                return self.safe_eval(f"({expr})") % 2 == 1
            if "reaches end of" in text:
                a, b = text.split("reaches end of")
                return self.safe_eval(f"({a.strip()})") >= len(self.safe_eval(f"({b.strip()})"))
    
            self.output_log.append(f"[ERROR] Unrecognized condition: {text}")
            return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition evaluation failed: {e} — in ({text})")
            return False

    def get_output(self):
        return '\n'.join(str(x) for x in self.output_log)

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
