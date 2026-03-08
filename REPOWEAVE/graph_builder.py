import networkx as nx


class GraphBuilder:
    def __init__(self):
        self.graph = nx.MultiDiGraph()  # Use MultiDiGraph to count parallel edges
        self.file_nodes = set()
        self.function_nodes = set()

    def _add_file_node(self, file_path, is_python=True):
        if file_path not in self.file_nodes:
            self.graph.add_node(file_path, type="python_file" if is_python else "data_file")
            self.file_nodes.add(file_path)

    def add_python_files(self, python_files):
        for f in python_files:
            self._add_file_node(f, is_python=True)

    def add_data_files(self, data_files):
        for df in data_files:
            self._add_file_node(df["path"], is_python=False)

    def add_functions(self, functions):
        """
        Add function nodes to the graph.
        Functions can have either 'name' or 'function_name' key.
        """
        for func in functions:
            # Handle different possible key names for the function name
            func_name = None
            if "name" in func:
                func_name = func["name"]
            elif "function_name" in func:
                func_name = func["function_name"]
            else:
                # Skip if no name found
                print(f"Warning: Function dict missing name key: {func}")
                continue

            func_id = f"{func['file']}::{func_name}"

            if func_id not in self.function_nodes:
                self.graph.add_node(
                    func_id,
                    type="function",
                    file=func['file'],
                    name=func_name
                )
                self.function_nodes.add(func_id)

    def add_calls(self, calls):
        """
        Add function call edges.
        Calls can have different key structures.
        """
        for call in calls:
            # Get caller file - could be 'file' or 'caller_file'
            caller_file = None
            if "caller_file" in call:
                caller_file = call["caller_file"]
            elif "file" in call:
                caller_file = call["file"]
            else:
                print(f"Warning: Call dict missing file/caller_file key: {call}")
                continue

            # Get called function name - could be 'called_function', 'function', or 'name'
            called_name = None
            if "called_function" in call:
                called_name = call["called_function"]
            elif "function" in call:
                called_name = call["function"]
            elif "name" in call:
                called_name = call["name"]
            else:
                print(f"Warning: Call dict missing function name: {call}")
                continue

            # Ensure caller file node exists
            self._add_file_node(caller_file, is_python=True)

            # Find target function node (if any) - look for function with matching name
            target_func = None
            for node, data in self.graph.nodes(data=True):
                if data.get("type") == "function" and data.get("name") == called_name:
                    target_func = node
                    break

            if target_func is None:
                # Create undefined function node
                target_func = f"UNDEF::{called_name}"
                self.graph.add_node(
                    target_func,
                    type="function",
                    defined=False,
                    name=called_name
                )

            # Add edge with multiplicity counting
            if self.graph.has_edge(caller_file, target_func):
                # increment count
                current_count = self.graph[caller_file][target_func][0].get('count', 1)
                self.graph[caller_file][target_func][0]['count'] = current_count + 1
            else:
                self.graph.add_edge(caller_file, target_func, relation="CALLS", count=1)

    def add_imports(self, resolved_imports):
        """Add import edges between files."""
        for imp in resolved_imports:
            source = imp["source"]
            target = imp["target"]

            # Ensure both file nodes exist
            self._add_file_node(source, is_python=True)
            self._add_file_node(target, is_python=True)

            if self.graph.has_edge(source, target):
                current_count = self.graph[source][target][0].get('count', 1)
                self.graph[source][target][0]['count'] = current_count + 1
            else:
                self.graph.add_edge(source, target, relation=imp["relation"], count=1)

    def add_data_usage(self, data_usage):
        """
        Add data usage edges (READ/WRITE/APPEND) from files to datasets.
        """
        for usage in data_usage:
            source_file = usage["file"]

            # Get dataset path - could be 'dataset' or 'path' key
            target_path = None
            if "dataset" in usage:
                target_path = usage["dataset"]
            elif "path" in usage:
                target_path = usage["path"]
            else:
                print(f"Warning: Data usage missing dataset/path: {usage}")
                continue

            if not target_path:
                continue

            # Ensure source file node exists
            self._add_file_node(source_file, is_python=True)

            # Add dataset node
            self.graph.add_node(target_path, type="data_file")

            # Add edge with multiplicity
            if self.graph.has_edge(source_file, target_path):
                current_count = self.graph[source_file][target_path][0].get('count', 1)
                self.graph[source_file][target_path][0]['count'] = current_count + 1
            else:
                self.graph.add_edge(
                    source_file,
                    target_path,
                    relation=usage["operation"],
                    count=1
                )

    def get_graph(self):
        return self.graph