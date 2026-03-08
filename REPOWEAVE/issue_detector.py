import os


class IssueDetector:
    def __init__(self, repo_root):
        self.repo_root = repo_root

    def detect_unused_functions(self, functions, calls):
        """Detect functions that are defined but never called"""
        called_functions = set()
        for call in calls:
            called_functions.add(call["called_function"])

        # Also check call edges in graph (more accurate)
        # But keep simple for now

        unused = []
        for func in functions:
            if func["function_name"] not in called_functions:
                unused.append({
                    "type": "UNUSED_FUNCTION",
                    "function": func["function_name"],
                    "file": func["file"]
                })
        return unused

    def detect_data_written_not_read(self, writes, reads):
        """Detect datasets written but never read"""
        read_datasets = set()
        for r in reads:
            if r.get("dataset"):
                read_datasets.add(r["dataset"])

        issues = []
        for write in writes:
            dataset = write.get("dataset")
            if dataset and dataset not in read_datasets:
                issues.append({
                    "type": "DATA_NEVER_READ",
                    "dataset": dataset,
                    "file": write["file"]
                })
        return issues

    def detect_calls_without_definition(self, functions, calls):
        """Detect functions that are called but not defined in repo"""
        defined_functions = set()
        for func in functions:
            defined_functions.add(func["function_name"])

        issues = []
        for call in calls:
            if call["called_function"] not in defined_functions:
                # Check if it might be a method call (obj.method())
                if '.' in call["called_function"]:
                    continue  # Skip method calls for now

                issues.append({
                    "type": "UNDEFINED_FUNCTION_CALL",
                    "function": call["called_function"],
                    "file": call["file"]
                })
        return issues

    def detect_missing_data_files(self, data_usage):
        """Detect data files that are read but don't exist"""
        issues = []
        for usage in data_usage:
            if usage["operation"] == "READ":
                path = usage.get("path") or usage.get("dataset")
                if path:
                    full_path = os.path.join(self.repo_root, path)
                    if not os.path.isfile(full_path):
                        issues.append({
                            "type": "MISSING_DATA_FILE",
                            "file": usage["file"],
                            "data_file": path
                        })
        return issues

    def run_all_checks(self, graph, functions, calls, resolved_imports, data_usage, data_files):
        """Run all issue detection rules"""
        issues = []

        # Extract writes and reads from data_usage
        writes = [du for du in data_usage if du["operation"] in ("WRITE", "APPEND")]
        reads = [du for du in data_usage if du["operation"] == "READ"]

        issues.extend(self.detect_unused_functions(functions, calls))
        issues.extend(self.detect_data_written_not_read(writes, reads))
        issues.extend(self.detect_calls_without_definition(functions, calls))
        issues.extend(self.detect_missing_data_files(data_usage))

        # Format issues as strings
        formatted_issues = []
        for issue in issues:
            if issue["type"] == "UNUSED_FUNCTION":
                formatted_issues.append(f"Unused function: {issue['function']} in {issue['file']}")
            elif issue["type"] == "DATA_NEVER_READ":
                formatted_issues.append(f"Data written but never read: {issue['dataset']} in {issue['file']}")
            elif issue["type"] == "UNDEFINED_FUNCTION_CALL":
                formatted_issues.append(f"Undefined function called: {issue['function']} in {issue['file']}")
            elif issue["type"] == "MISSING_DATA_FILE":
                formatted_issues.append(f"Data file read but not found: {issue['data_file']} in {issue['file']}")

        return formatted_issues