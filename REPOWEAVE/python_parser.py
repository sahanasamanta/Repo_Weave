import ast
import os


class PythonParser:
    def parse_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        visitor = _PythonASTVisitor(file_path)
        visitor.visit(tree)
        return {
            "functions": visitor.functions,
            "calls": visitor.calls,
            "imports": visitor.imports,
            "data_usage": visitor.data_usage
        }


class _PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.functions = []  # list of function names
        self.calls = []  # list of called function names (by name)
        self.imports = []  # raw import info
        self.data_usage = []  # list of (op, path_string)

    def visit_FunctionDef(self, node):
        self.functions.append({
            "function_name": node.name,  # Consistent key name
            "file": self.file_path,
            "line": node.lineno
        })
        self.generic_visit(node)

    def visit_Call(self, node):
        # Extract function name (simplified)
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name:
            self.calls.append({
                "file": self.file_path,
                "called_function": func_name,  # Consistent key name
                "line": node.lineno
            })

        # Detect data file accesses
        self._detect_data_access(node)
        self.generic_visit(node)

    def _detect_data_access(self, node):
        # Look for calls that might read/write files
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == 'open':
                # open(file, mode)
                if node.args:
                    path = self._extract_string(node.args[0])
                    mode = 'r'
                    for kw in node.keywords:
                        if kw.arg == 'mode':
                            mode = self._extract_string(kw.value) or 'r'
                    op = 'write' if 'w' in mode or 'a' in mode or '+' in mode else 'read'
                    if path:
                        self.data_usage.append({
                            "file": self.file_path,
                            "operation": op.upper(),
                            "dataset": path,  # Use 'dataset' for consistency
                            "line": node.lineno
                        })
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            # Common data libraries
            if attr in ('read_csv', 'read_excel', 'read_json', 'load'):
                # pandas read, json.load, etc.
                if node.args:
                    path = self._extract_string(node.args[0])
                    if path:
                        self.data_usage.append({
                            "file": self.file_path,
                            "operation": "READ",
                            "dataset": path,
                            "line": node.lineno
                        })
            elif attr in ('to_csv', 'to_excel', 'to_json', 'dump', 'save'):
                if node.args:
                    path = self._extract_string(node.args[0])
                    if path:
                        op = "APPEND" if any(kw.arg == 'mode' and self._extract_string(kw.value) == 'a' for kw in
                                             node.keywords) else "WRITE"
                        self.data_usage.append({
                            "file": self.file_path,
                            "operation": op,
                            "dataset": path,
                            "line": node.lineno
                        })

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({
                "file": self.file_path,
                "module": alias.name,
                "alias": alias.asname,
                "type": "import"
            })

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                "file": self.file_path,
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "type": "importfrom"
            })

    def _extract_string(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        # Could add more handling (e.g., f-strings, variables) but keep simple
        return None