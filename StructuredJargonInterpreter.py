import re
from AskException import AskException

class StructuredJargonInterpreter:
    def __init__(self):
        self.memory = {}
        self.output_log = []
        self.max_steps = 1000
        self.break_loop = False
        self.pending_ask = None
        self.resume_context = None

    def run(self, code: str, memory: dict):
        self.code = code
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.memory = memory.copy()
        self.output_log = ["[No output returned]"]
        self.break_loop = False
        self.pending_ask = None
        self.resume_context = {
            "type": "main",
            "block": self.lines,
            "index": 0,
            "loop": None
        }

        try:
            self.execute_block(self.lines)
        except AskException as e:
            self.pending_ask = e

        return {
            "output": self.output_log,
            "memory": self.memory
        }

    def resume(self, code: str, memory: dict, var: str = None, value: str = None):
        self.code = code
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.memory = memory.copy()
        self.break_loop = False

        if var and value is not None:
            self.memory[var] = value

        self.pending_ask = None

        try:
            self.resume_loop()
        except AskException as e:
            self.pending_ask = e

        if not self.output_log:
            self.output_log = ["[No output returned]"]

        return {
            "output": self.output_log,
            "memory": self.memory
        }

    def resume_loop(self):
        ctx = self.resume_context
        if ctx["type"] == "main":
            self.execute_block(ctx["block"], ctx["index"])
        elif ctx["type"] == "repeat_n":
            self.handle_repeat_n_times(ctx["block"], ctx["loop"]["times"], ctx["loop"]["counter"])
        elif ctx["type"] == "repeat_until":
            self.handle_repeat_until(ctx["block"])
        elif ctx["type"] == "repeat_each":
            self.handle_repeat_for_each(ctx["block"], ctx["loop"]["iterable"], ctx["loop"]["index"], ctx["loop"]["var"])

    def execute_block(self, block, start_index=0):
        i = start_index
        steps = 0
        while i < len(block):
            line = block[i]
            steps += 1
            if steps > self.max_steps:
                self.output_log.append("[ERROR] Execution stopped: Too many steps (possible infinite loop).")
                break
            self.resume_context = {
                "type": "main",
                "block": block,
                "index": i + 1
            }

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

            if self.pending_ask:
                return
            i += 1

    def handle_repeat_n_times(self, block, total=None, start=0):
        match = re.match(r'REPEAT\s+(\d+)\s+times', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT syntax: {block[0]}")
            return
        times = int(match.group(1)) if total is None else total

        for i in range(start, times):
            self.break_loop = False
            self.resume_context = {
                "type": "repeat_n",
                "block": block,
                "loop": {"times": times, "counter": i}
            }
            self.execute_block(block[1:-1])
            if self.pending_ask or self.break_loop:
                return

    def handle_repeat_until(self, block):
        condition_line = block[0].replace("REPEAT_UNTIL", "").strip()
        count = 0
        while not self.evaluate_condition(condition_line):
            self.break_loop = False
            self.resume_context = {
                "type": "repeat_until",
                "block": block
            }
            self.execute_block(block[1:-1])
            if self.pending_ask or self.break_loop:
                return
            count += 1
            if count > self.max_steps:
                self.output_log.append("[ERROR] Loop exceeded max iterations.")
                break

    def handle_repeat_for_each(self, block, iterable=None, start=0, var=None):
        match = re.match(r'REPEAT_FOR_EACH\s+(\w+)\s+in\s+(\w+)', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT_FOR_EACH syntax: {block[0]}")
            return
        loop_var, list_name = match.groups()
        values = self.memory.get(list_name, []) if iterable is None else iterable
        for i in range(start, len(values)):
            self.memory[loop_var] = values[i]
            self.break_loop = False
            self.resume_context = {
                "type": "repeat_each",
                "block": block,
                "loop": {"var": loop_var, "iterable": values, "index": i}
            }
            self.execute_block(block[1:-1])
            if self.pending_ask or self.break_loop:
                return

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
        if "[No output returned]" in self.output_log:
            self.output_log.remove("[No output returned]")
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
        question, var = match.groups()
        if var in self.memory and self.memory[var] not in ["", None]:
            return
        self.memory[var] = ""
        raise AskException(question, var)

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
                return all(self.evaluate_condition(p.strip()) for p in text.split("AND"))
            if "OR" in text:
                return any(self.evaluate_condition(p.strip()) for p in text.split("OR"))
            if "is equal to" in text:
                a, b = text.split("is equal to")
                return self.safe_eval(a) == self.safe_eval(b)
            if "is not equal to" in text:
                a, b = text.split("is not equal to")
                return self.safe_eval(a) != self.safe_eval(b)
            if "is greater than or equal to" in text:
                a, b = text.split("is greater than or equal to")
                return self.safe_eval(a) >= self.safe_eval(b)
            if "is less than or equal to" in text:
                a, b = text.split("is less than or equal to")
                return self.safe_eval(a) <= self.safe_eval(b)
            if "is greater than" in text:
                a, b = text.split("is greater than")
                return self.safe_eval(a) > self.safe_eval(b)
            if "is less than" in text:
                a, b = text.split("is less than")
                return self.safe_eval(a) < self.safe_eval(b)
            if "is even" in text:
                return self.safe_eval(text.split("is even")[0]) % 2 == 0
            if "is odd" in text:
                return self.safe_eval(text.split("is odd")[0]) % 2 == 1
            if "is in" in text:
                a, b = text.split("is in")
                return self.safe_eval(a) in self.safe_eval(b)
            if "reaches end of" in text:
                a, b = text.split("reaches end of")
                return self.safe_eval(a) >= len(self.safe_eval(b))
            self.output_log.append(f"[ERROR] Unrecognized condition: {text}")
            return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition evaluation failed: {e} — in ({text})")
            return False

    def get_output(self):
        return '\n'.join(str(x) for x in self.output_log)
