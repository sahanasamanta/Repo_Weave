import os

class ImportResolver:
    def __init__(self, repo_root):
        self.repo_root = repo_root

    def resolve_imports(self, raw_imports):
        """
        raw_imports: list of dicts from parser
        Returns list of resolved edges: (source_file, target_file, relationship)
        """
        resolved = []
        for imp in raw_imports:
            source = imp["file"]
            if imp["type"] == "import":
                module_parts = imp["module"].split('.')
                # Try to find a corresponding .py file
                target = self._module_to_path(module_parts)
                if target:
                    resolved.append({
                        "source": source,
                        "target": target,
                        "relation": "IMPORTS"
                    })
            else:  # importfrom
                module_parts = imp["module"].split('.')
                base_target = self._module_to_path(module_parts)
                if base_target:
                    # For 'from module import name', we could also link to the specific object,
                    # but for simplicity link to the module file.
                    resolved.append({
                        "source": source,
                        "target": base_target,
                        "relation": "IMPORTS"
                    })
                # Also could resolve the imported name to a function/class within the module,
                # but that requires parsing the target file. We'll skip for now.
        return resolved

    def _module_to_path(self, module_parts):
        """Convert module parts like ['package', 'sub', 'module'] to file path."""
        # Try as package.module
        rel_path = os.path.join(*module_parts) + '.py'
        full_path = os.path.join(self.repo_root, rel_path)
        if os.path.isfile(full_path):
            return rel_path
        # Try as package/module/__init__.py
        init_path = os.path.join(*module_parts, '__init__.py')
        full_init = os.path.join(self.repo_root, init_path)
        if os.path.isfile(full_init):
            return init_path
        return None