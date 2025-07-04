import re
from AskException import AskException

class StructuredJargonInterpreter:
    def __init__(self):
        self.code = ""
        self.lines = []
        self.memory = {}
        self.output_log = []
        self.pending_ask = None
        self.current_line_index = 0
        self.max_steps = 1000
        self.break_loop = False
        self.loop_stack = []
        self.resume_line_index = 0

    def run(self, code: str, memory: dict):
        self.code = code
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.memory = memory.copy()
        self.output_log = []
        self.pending_ask = None
        self.current_line_index = 0
        self.break_loop = False
        self.resume_line_index = 0
        self.loop_stack = []

        try:
            self.execute()
        except AskException as e:
            self.pending_ask = e

        return {
            "output": self.output_log,
            "memory": self.memory
        }

    def resume(self, code: str, memory: dict):
        self.code = code
        self.lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        self.memory.update(memory)
        self.output_log = []
        self.pending_ask = None
        self.break_loop = False

        try:
            if self.loop_stack:
                loop_type, block, i, count = self.loop_stack.pop()
                for j in range(i + 1, count):
                    self.loop_stack.append((loop_type, block, j, count))
                    self.execute_block(block[1:-1])
                    self.loop_stack.pop()
                    if self.pending_ask:
                        raise self.pending_ask
                    if self.break_loop:
                        self.break_loop = False
                        break
                return {
                    "output": self.output_log,
                    "memory": self.memory
                }

            self.current_line_index = self.resume_line_index
            self.execute()
        except AskException as e:
            self.pending_ask = e

        return {
            "output": self.output_log,
            "memory": self.memory
        }

    def execute(self):
        steps = 0
        while self.current_line_index < len(self.lines):
            if steps >= self.max_steps:
                self.output_log.append("[ERROR] Execution stopped: Too many steps.")
                break
            steps += 1

            line = self.lines[self.current_line_index]

            if self.break_loop:
                self.break_loop = False
                self.current_line_index += 1
                continue

            if line == "BREAK":
                self.break_loop = True
            elif line.startswith("SET "):
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
                block, jump = self.collect_block("IF", "END")
                self.handle_if_else(block)
                self.current_line_index = jump
                continue
            elif line.startswith("REPEAT "):
                block, jump = self.collect_block("REPEAT", "END")
                self.handle_repeat_n_times(block)
                self.current_line_index = jump
                continue
            elif line.startswith("REPEAT_UNTIL"):
                block, jump = self.collect_block("REPEAT_UNTIL", "END")
                self.handle_repeat_until(block)
                self.current_line_index = jump
                continue
            elif line.startswith("REPEAT_FOR_EACH"):
                block, jump = self.collect_block("REPEAT_FOR_EACH", "END")
                self.handle_repeat_for_each(block)
                self.current_line_index = jump
                continue
            else:
                self.output_log.append(f"[ERROR] Unknown command: {line}")

            self.current_line_index += 1
            if self.pending_ask:
                raise self.pending_ask

    def collect_block(self, start_kw, end_kw):
        block = [self.lines[self.current_line_index]]
        i = self.current_line_index + 1
        nested = 1
        while i < len(self.lines):
            line = self.lines[i]
            if line.startswith(start_kw):
                nested += 1
            elif line == end_kw:
                nested -= 1
                if nested == 0:
                    block.append(line)
                    break
            block.append(line)
            i += 1
        return block, i + 1

    def collect_block_from(self, lines, start_index, start_kw, end_kw):
        block = [lines[start_index]]
        i = start_index + 1
        nested = 1
        while i < len(lines):
            line = lines[i]
            if line.startswith(start_kw):
                nested += 1
            elif line == end_kw:
                nested -= 1
                if nested == 0:
                    block.append(line)
                    break
            block.append(line)
            i += 1
        return block, i + 1

    def handle_set(self, line):
        match = re.match(r'SET\s+(\w+)\[(.+?)\]\s*\((.+)\)', line)
        if match:
            var, idx_expr, val_expr = match.groups()
            index = self.safe_eval(idx_expr)
            value = self.safe_eval(val_expr)
            if var in self.memory and isinstance(self.memory[var], list):
                self.memory[var][index] = value
            else:
                self.output_log.append(f"[ERROR] {var} is not a list")
        else:
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

    def handle_add(self, line):
        match = re.match(r'ADD\s+(.+?)\s+to\s+(\w+)', line)
        if match:
            val_expr, var = match.groups()
            value = self.safe_eval(val_expr)
            if var not in self.memory or not isinstance(self.memory[var], list):
                self.memory[var] = []
            self.memory[var].append(value)
        else:
            self.output_log.append(f"[ERROR] Invalid ADD syntax: {line}")

    def handle_remove(self, line):
        match = re.match(r'REMOVE\s+(.+?)\s+from\s+(\w+)', line)
        if match:
            val_expr, var = match.groups()
            value = self.safe_eval(val_expr)
            if var in self.memory and isinstance(self.memory[var], list):
                try:
                    self.memory[var].remove(value)
                except ValueError:
                    self.output_log.append(f"[ERROR] Value {value} not found in {var}")
            else:
                self.output_log.append(f"[ERROR] {var} is not a list")
        else:
            self.output_log.append(f"[ERROR] Invalid REMOVE syntax: {line}")

    def handle_ask(self, line):
        match = re.match(r'ASK\s+"(.+?)"\s+as\s+(\w+)', line)
        if match:
            question, var = match.groups()
            val = self.memory.get(var, "")
            if val is None or (isinstance(val, str) and val.strip() == ""):
                raise AskException(question, var)
        else:
            self.output_log.append(f"[ERROR] Invalid ASK syntax: {line}")

    def handle_if_else(self, block):
        condition_line = block[0]
        condition = condition_line.replace("IF", "").replace("THEN", "").strip()
        condition_result = self.evaluate_condition(condition)

        true_block, false_block = [], []
        current_block = true_block
        i = 1
        while i < len(block) - 1:
            line = block[i]
            if line == "ELSE":
                current_block = false_block
            else:
                current_block.append(line)
            i += 1

        try:
            self.execute_block(true_block if condition_result else false_block)
        except AskException as e:
            raise e

    def handle_repeat_n_times(self, block):
        match = re.match(r'REPEAT\s+(\d+)\s+times', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT syntax: {block[0]}")
            return
        count = int(match.group(1))
        start_index = 0

        if self.loop_stack and self.loop_stack[-1][1] == block:
            _, _, i, saved_count = self.loop_stack.pop()
            start_index = i + 1
            count = saved_count

        for i in range(start_index, count):
            try:
                self.loop_stack.append(("REPEAT", block, i, count))
                self.execute_block(block[1:-1])
                self.loop_stack.pop()
            except AskException as e:
                raise e
            if self.pending_ask:
                return
            if self.break_loop:
                self.break_loop = False
                break

    def handle_repeat_until(self, block):
        condition = block[0].replace("REPEAT_UNTIL", "").strip()
        while not self.evaluate_condition(condition):
            try:
                self.execute_block(block[1:-1])
            except AskException as e:
                self.loop_stack.append(("REPEAT_UNTIL", block, 0, 0))
                raise e
            if self.pending_ask:
                return
            if self.break_loop:
                self.break_loop = False
                break

    def handle_repeat_for_each(self, block):
        match = re.match(r'REPEAT_FOR_EACH\s+(\w+)\s+in\s+(\w+)', block[0])
        if not match:
            self.output_log.append(f"[ERROR] Invalid REPEAT_FOR_EACH syntax: {block[0]}")
            return
        var, iterable = match.groups()
        items = self.memory.get(iterable, [])
        if not isinstance(items, list):
            self.output_log.append(f"[ERROR] {iterable} is not a list")
            return
        start_index = 0
        if self.loop_stack and self.loop_stack[-1][0] == "REPEAT_FOR_EACH":
            _, _, saved_index, _ = self.loop_stack.pop()
            start_index = saved_index + 1

        for i in range(start_index, len(items)):
            self.memory[var] = items[i]
            try:
                self.loop_stack.append(("REPEAT_FOR_EACH", block, i, len(items)))
                self.execute_block(block[1:-1])
                self.loop_stack.pop()
            except AskException as e:
                raise e
            if self.pending_ask:
                return
            if self.break_loop:
                self.break_loop = False
                break

    def execute_block(self, lines):
        index = 0
        steps = 0
        while index < len(lines):
            if steps >= self.max_steps:
                self.output_log.append("[ERROR] Execution stopped: Too many steps.")
                break
            steps += 1

            line = lines[index]
            if line == "BREAK":
                self.break_loop = True
                break
            elif line.startswith("SET "):
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
                block, jump = self.collect_block_from(lines, index, "IF", "END")
                self.handle_if_else(block)
                index = jump
                continue
            elif line.startswith("REPEAT "):
                block, jump = self.collect_block_from(lines, index, "REPEAT", "END")
                self.handle_repeat_n_times(block)
                index = jump
                continue
            elif line.startswith("REPEAT_UNTIL"):
                block, jump = self.collect_block_from(lines, index, "REPEAT_UNTIL", "END")
                self.handle_repeat_until(block)
                index = jump
                continue
            elif line.startswith("REPEAT_FOR_EACH"):
                block, jump = self.collect_block_from(lines, index, "REPEAT_FOR_EACH", "END")
                self.handle_repeat_for_each(block)
                index = jump
                continue
            else:
                self.output_log.append(f"[ERROR] Unknown command in block: {line}")

            if self.pending_ask:
                raise self.pending_ask
            index += 1

    def safe_eval(self, expr):
        try:
            return eval(expr, {"__builtins__": None}, {
                "int": int, "float": float, "str": str, "len": len, "bool": bool,
                **self.memory
            })
        except Exception as e:
            self.output_log.append(f"[ERROR] Eval failed: {e} in ({expr})")
            return None

    def evaluate_condition(self, cond):
        try:
            if "AND" in cond:
                return all(self.evaluate_condition(p.strip()) for p in cond.split("AND"))
            elif "OR" in cond:
                return any(self.evaluate_condition(p.strip()) for p in cond.split("OR"))
            elif "is equal to" in cond:
                a, b = cond.split("is equal to")
                return self.safe_eval(a) == self.safe_eval(b)
            elif "is not equal to" in cond:
                a, b = cond.split("is not equal to")
                return self.safe_eval(a) != self.safe_eval(b)
            elif "is greater than or equal to" in cond:
                a, b = cond.split("is greater than or equal to")
                return self.safe_eval(a) >= self.safe_eval(b)
            elif "is less than or equal to" in cond:
                a, b = cond.split("is less than or equal to")
                return self.safe_eval(a) <= self.safe_eval(b)
            elif "is greater than" in cond:
                a, b = cond.split("is greater than")
                return self.safe_eval(a) > self.safe_eval(b)
            elif "is less than" in cond:
                a, b = cond.split("is less than")
                return self.safe_eval(a) < self.safe_eval(b)
            elif "is in" in cond:
                a, b = cond.split("is in")
                return self.safe_eval(a) in self.safe_eval(b)
            elif "is even" in cond:
                return self.safe_eval(cond.split("is even")[0]) % 2 == 0
            elif "is odd" in cond:
                return self.safe_eval(cond.split("is odd")[0]) % 2 == 1
            return False
        except Exception as e:
            self.output_log.append(f"[ERROR] Condition evaluation failed: {e} in ({cond})")
            return False
