import re

class AskException(Exception):
    def __init__(self, prompt, variable):
        self.prompt = prompt
        self.variable = variable

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.max_steps = 1000
        self.break_loop = False
        self.pending_ask = None
        self.pending_question = None
        self.answers = []
        self.answer_index = 0

    def run(self, code: str, preset_answers: dict = None):
        self.memory.clear()
        self.output_log.clear()
        self.break_loop = False
        self.pending_ask = None

        if preset_answers:
            self.memory.update(preset_answers)

        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]

        try:
            self.execute_block(self.lines)
        except AskException as e:
            self.pending_ask = e

        return {
            "output": self.output_log if self.output_log else ["[No output returned]"],
            "memory": self.memory,
            "ask": self.pending_question["prompt"] if self.pending_question else None,
            "ask_var": self.pending_question["variable"] if self.pending_question else None
        }

    def execute_block(self, block):
        i = 0
        steps = 0
        while i < len(block):
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
                self.handle_ask(line)
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
            return
        prompt, var = match.groups()
        
        if self.answer_index < len(self.answers):
            raw = self.answers[self.answer_index]
            self.answer_index += 1
    
            try:
                value = int(raw)
            except ValueError:
                value = raw
    
            self.memory[var] = value
        else:
            self.pending_question = {
                "prompt": prompt,
                "variable": var
            }
            raise AskException(prompt, var)

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
            if self.break_loop or self.pending_ask:
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
            if self.break_loop or self.pending_ask:
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
            if self.break_loop or self.pending_ask:
                break

    def safe_eval(self, expr):
        expr = expr.strip()
        try:
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
            elif "is equal to" in text:
                a, b = text.split("is equal to")
                return self.safe_eval(a) == self.safe_eval(b)
            elif "is not equal to" in text:
                a, b = text.split("is not equal to")
                return self.safe_eval(a) != self.safe_eval(b)
            elif "is greater than or equal to" in text:
                a, b = text.split("is greater than or equal to")
                return self.safe_eval(a) >= self.safe_eval(b)
            elif "is less than or equal to" in text:
                a, b = text.split("is less than or equal to")
                return self.safe_eval(a) <= self.safe_eval(b)
            elif "is greater than" in text:
                a, b = text.split("is greater than")
                return self.safe_eval(a) > self.safe_eval(b)
            elif "is less than" in text:
                a, b = text.split("is less than")
                return self.safe_eval(a) < self.safe_eval(b)
            elif "is even" in text:
                return self.safe_eval(text.split("is even")[0]) % 2 == 0
            elif "is odd" in text:
                return self.safe_eval(text.split("is odd")[0]) % 2 == 1
            elif "is in" in text:
                a, b = text.split("is in")
                return self.safe_eval(a) in self.safe_eval(b)
            elif "reaches end of" in text:
                a, b = text.split("reaches end of")
                return self.safe_eval(a) >= len(self.safe_eval(b))
            else:
                self.output_log.append(f"[ERROR] Unrecognized condition: {text}")
                return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition evaluation failed: {e} — in ({text})")
            return False
