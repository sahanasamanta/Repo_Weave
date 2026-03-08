import os
import sys
import argparse
from repo_loader import RepoLoader
from python_parser import PythonParser
from data_file_analyzer import DataFileAnalyzer
from import_resolver import ImportResolver
from graph_builder import GraphBuilder
from issue_detector import IssueDetector
from graph_visualizer import GraphVisualizer
from graph_exporter import GraphExporter

# Try to import interactive exporter
try:
    from graph_interactive import GraphInteractiveExporter

    INTERACTIVE_AVAILABLE = True
except ImportError:
    INTERACTIVE_AVAILABLE = False
    print("Note: graph_interactive module not found. Interactive HTML export disabled.")

# Common library functions that should not be reported as undefined
COMMON_LIBRARIES = {
    'streamlit': [
        'set_page_config', 'title', 'file_uploader', 'image', 'write',
        'spinner', 'success', 'subheader', 'markdown', 'sidebar',
        'columns', 'expander', 'button', 'checkbox', 'radio', 'selectbox',
        'multiselect', 'slider', 'text_input', 'number_input', 'text_area',
        'date_input', 'time_input', 'file_uploader', 'camera_input',
        'color_picker', 'balloons', 'snow', 'error', 'warning', 'info',
        'progress', 'empty', 'stop'
    ],
    'torch': [
        'load', 'save', 'no_grad', 'argmax', 'tensor', 'FloatTensor',
        'LongTensor', 'nn', 'optim', 'utils', 'cuda', 'cpu', 'eval',
        'train', 'item', 'load_state_dict', 'mobilenet_v2', 'Linear',
        'model', 'softmax', 'relu', 'dropout', 'conv2d', 'max_pool2d',
        'adaptive_avg_pool2d', 'view', 'unsqueeze', 'squeeze', 'cat',
        'stack', 'split', 'chunk', 'gather', 'scatter', 'masked_select'
    ],
    'torchvision': [
        'models', 'transforms', 'datasets', 'Compose', 'Resize',
        'ToTensor', 'Normalize', 'mobilenet_v2', 'resnet18', 'vgg16',
        'alexnet', 'densenet', 'inception_v3', 'googlenet'
    ],
    'PIL': [
        'Image', 'ImageDraw', 'ImageFont', 'ImageFilter', 'open',
        'convert', 'resize', 'crop', 'rotate', 'save', 'show',
        'new', 'blend', 'composite', 'merge'
    ],
    'transformers': [
        'pipeline', 'AutoModel', 'AutoTokenizer', 'AutoModelForSequenceClassification',
        'AutoModelForQuestionAnswering', 'AutoModelForTokenClassification',
        'AutoModelForMaskedLM', 'AutoModelForCausalLM'
    ],
    'numpy': [
        'array', 'zeros', 'ones', 'reshape', 'argmax', 'max', 'min',
        'mean', 'std', 'var', 'sum', 'prod', 'dot', 'matmul', 'transpose',
        'expand_dims', 'squeeze', 'concatenate', 'stack', 'split'
    ],
    'pandas': [
        'read_csv', 'to_csv', 'read_excel', 'to_excel', 'read_json',
        'to_json', 'DataFrame', 'Series', 'concat', 'merge', 'join',
        'pivot_table', 'crosstab', 'cut', 'qcut'
    ],
    'python_builtins': [
        'open', 'read', 'write', 'close', 'print', 'len', 'range',
        'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
        'min', 'max', 'sum', 'any', 'all', 'abs', 'round', 'int',
        'float', 'str', 'list', 'dict', 'set', 'tuple', 'bool'
    ]
}


def is_library_function(func_name):
    """Check if a function name belongs to common libraries."""
    if not func_name:
        return False
    func_lower = func_name.lower()
    for library, functions in COMMON_LIBRARIES.items():
        if func_lower in [f.lower() for f in functions]:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Analyze a GitHub repository and generate dependency graphs.")
    parser.add_argument("repo_url", nargs="?",
                        default="https://github.com/sahanasamanta/AI-Powered-X-Ray-Report-Generator-",
                        help="URL of the GitHub repository")
    parser.add_argument("--output-png", default="dependency_graph.png", help="Output PNG file name")
    parser.add_argument("--output-html", default="dependency_graph.html", help="Output HTML file name")
    parser.add_argument("--output-json", default="dependency_graph.json", help="Output JSON file name")
    parser.add_argument("--show-calls", action="store_true", help="Show intra-file calls (default: hide)")
    parser.add_argument("--no-png", action="store_true", help="Skip PNG generation")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML generation")
    parser.add_argument("--no-json", action="store_true", help="Skip JSON export")
    parser.add_argument("--ignore-libs", action="store_true", help="Ignore common library functions in issue detection")
    args = parser.parse_args()

    print("\n===== REPOSITORY ANALYSIS STARTED =====\n")
    print(f"Analyzing repository: {args.repo_url}")

    loader = RepoLoader(repo_url=args.repo_url)
    repo_path, file_map = loader.load_repository()

    python_parser = PythonParser()
    all_functions = []
    all_calls = []
    all_imports = []
    all_data_usage = []

    print("\n===== ANALYZING PYTHON FILES =====\n")
    for rel_py_file in file_map["python_files"]:
        full_py_path = os.path.join(repo_path, rel_py_file)
        print(f"Parsing: {rel_py_file}")
        result = python_parser.parse_file(full_py_path)

        # Debug: Print structure of first call to understand format
        if result["calls"] and len(result["calls"]) > 0:
            print(f"Sample call structure: {result['calls'][0]}")

        # Convert absolute paths to repo‑relative
        for func in result["functions"]:
            func["file"] = os.path.relpath(func["file"], repo_path)

        for call in result["calls"]:
            # Handle different possible key names
            if "caller_file" in call:
                call["caller_file"] = os.path.relpath(call["caller_file"], repo_path)
            elif "file" in call:
                call["file"] = os.path.relpath(call["file"], repo_path)

            # Ensure we have a function name field
            if "called_function" not in call and "function" in call:
                call["called_function"] = call["function"]
            elif "called_function" not in call and "name" in call:
                call["called_function"] = call["name"]

        for imp in result["imports"]:
            imp["file"] = os.path.relpath(imp["file"], repo_path)

        for du in result["data_usage"]:
            du["file"] = os.path.relpath(du["file"], repo_path)

        all_functions.extend(result["functions"])
        all_calls.extend(result["calls"])
        all_imports.extend(result["imports"])
        all_data_usage.extend(result["data_usage"])

    print(f"\nTotal functions: {len(all_functions)}")
    print(f"Total calls: {len(all_calls)}")
    if all_calls:
        print(f"Sample call keys: {list(all_calls[0].keys())}")

    resolver = ImportResolver(repo_path)
    resolved_imports = resolver.resolve_imports(all_imports)

    data_files = [{"path": rel_path} for rel_path in file_map["data_files"]]

    print("\n===== BUILDING GRAPH =====")
    builder = GraphBuilder()
    builder.add_python_files(file_map["python_files"])
    builder.add_data_files(data_files)
    builder.add_functions(all_functions)
    builder.add_calls(all_calls)
    builder.add_imports(resolved_imports)
    builder.add_data_usage(all_data_usage)

    graph = builder.get_graph()
    print(f"Graph nodes: {graph.number_of_nodes()}")
    print(f"Graph edges: {graph.number_of_edges()} (with multiplicity)")

    print("\n===== DETECTING ISSUES =====")
    detector = IssueDetector(repo_path)

    # Filter out library functions if requested
    filtered_calls = all_calls
    if args.ignore_libs and all_calls:
        filtered_calls = []
        library_calls_count = 0

        for call in all_calls:
            # Try different possible key names for the function name
            func_name = None
            if "called_function" in call:
                func_name = call["called_function"]
            elif "function" in call:
                func_name = call["function"]
            elif "name" in call:
                func_name = call["name"]

            if func_name and is_library_function(func_name):
                library_calls_count += 1
            else:
                filtered_calls.append(call)

        print(f"Ignored {library_calls_count} library function calls")
        print(f"Keeping {len(filtered_calls)} non-library calls")

    issues = detector.run_all_checks(
        graph,
        all_functions,
        filtered_calls,
        resolved_imports,
        all_data_usage,
        data_files
    )

    print(f"\nDetected Issues: {len(issues)}")
    if not issues:
        print("No issues found.")
    else:
        for issue in issues:
            print(f"  - {issue}")

    # Export JSON only once
    if not args.no_json:
        print("\n===== EXPORTING GRAPH =====")
        exporter = GraphExporter(graph)
        exporter.export_json(args.output_json)

    # Generate PNG
    if not args.no_png:
        print("\n===== GENERATING STATIC VISUALIZATION =====")
        visualizer = GraphVisualizer(graph, issues)
        visualizer.draw_graph(args.output_png, show_calls=args.show_calls)

    # Generate HTML if available
    # In main.py, replace the interactive section with:

    if not args.no_html:
        print("\n===== GENERATING INTERACTIVE VISUALIZATION =====")
        try:
            from graph_interactive import GraphInteractiveExporter
            interactive = GraphInteractiveExporter(graph, issues)
            html_file = args.output_html if args.output_html.endswith('.html') else args.output_html + '.html'
            interactive.export_html(html_file, show_calls=args.show_calls)
            print(f"📊 Open {html_file} in your browser")
        except ImportError:
            print("❌ Pyvis not installed. Run: pip install pyvis")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n===== ANALYSIS COMPLETE =====")

if __name__ == "__main__":
    main()