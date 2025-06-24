class BaseTokenizer:
    """Simple tokenizer for area files."""
    def __init__(self, lines):
        self.lines = [line.rstrip('\n') for line in lines]
        self.index = 0

    def next_line(self):
        while self.index < len(self.lines):
            line = self.lines[self.index].strip()
            self.index += 1
            if line.startswith('*') or line == '':
                continue
            return line
        return None

    def peek_line(self):
        pos = self.index
        line = self.next_line()
        self.index = pos
        return line

    def read_string_tilde(self):
        parts = []
        while True:
            line = self.next_line()
            if line is None:
                break
            if line.endswith('~'):
                parts.append(line[:-1])
                break
            parts.append(line)
        return '\n'.join(parts)

    def read_number(self):
        line = self.next_line()
        if line is None:
            raise ValueError('Unexpected EOF while reading number')
        return int(line.split()[0])
