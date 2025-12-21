class BaseTokenizer:
    """Simple tokenizer for area files."""

    def __init__(self, lines):
        self.lines = [line.rstrip("\n") for line in lines]
        self.index = 0

    def next_line(self):
        while self.index < len(self.lines):
            line = self.lines[self.index].strip()
            self.index += 1
            if line.startswith("*") or line == "":
                continue
            return line
        return None

    def peek_line(self):
        pos = self.index
        line = self.next_line()
        self.index = pos
        return line

    def _raw_line(self):
        """Read next line without skipping empty/comment lines."""
        if self.index < len(self.lines):
            line = self.lines[self.index]
            self.index += 1
            return line
        return None

    def read_string_tilde(self):
        parts = []
        while True:
            line = self._raw_line()
            if line is None:
                break
            # Check for tilde at end (may have trailing whitespace)
            stripped = line.rstrip()
            if stripped.endswith("~"):
                parts.append(stripped[:-1])
                break
            parts.append(line)
        return "\n".join(parts)

    def read_number(self):
        line = self.next_line()
        if line is None:
            raise ValueError("Unexpected EOF while reading number")
        return int(line.split()[0])
