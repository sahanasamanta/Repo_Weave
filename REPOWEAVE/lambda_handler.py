import json
import os
import sys
import tempfile
import shutil
import traceback
from pathlib import Path

# Import your existing modules
from repo_loader import RepoLoader
from python_parser import PythonParser
from data_file_analyzer import DataFileAnalyzer
from import_resolver import ImportResolver
from graph_builder import GraphBuilder
from issue_detector import IssueDetector
from graph_exporter import GraphExporter
from bedrock_helper import BedrockHelper  

def lambda_handler(event, context):
    """
    AWS Lambda entry point with robust error handling
    """
    try:
        print(" Event received:", json.dumps(event))
        
        # SAFELY extract repo_url from different possible sources
        repo_url = None
        
        # Check direct event parameter
        if isinstance(event, dict):
            repo_url = event.get('repo_url')
            
            # Check query string parameters (for GET requests)
            if not repo_url and event.get('queryStringParameters'):
                repo_url = event.get('queryStringParameters').get('repo_url')
            
            # Check body (for POST requests)
            if not repo_url and event.get('body'):
                try:
                    body = json.loads(event['body'])
                    repo_url = body.get('repo_url')
                except:
                    pass
        
        if not repo_url:
            print(" No repository URL provided")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No repository URL provided. Please provide a repo_url parameter.'})
            }
        
        print(f" Analyzing repository: {repo_url}")
        
        # Create a temporary directory for cloning
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f" Working in temp directory: {tmpdir}")
            
            # Change to temp directory
            original_dir = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                # Run your analysis
                result = analyze_repository(repo_url)
                print("Analysis completed successfully")
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(result)
                }
                
            finally:
                # Always change back to original directory
                os.chdir(original_dir)
            
    except Exception as e:
        print(" ERROR:", str(e))
        print(" TRACEBACK:", traceback.format_exc())
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc().split('\n')
            })
        }

def analyze_repository(repo_url):
    """Your existing analysis logic with added safety checks"""
    
    try:
        # Initialize loader
        loader = RepoLoader(repo_url=repo_url)
        repo_path, file_map = loader.load_repository()
        
        # SAFETY CHECK: Ensure file_map has required keys
        if not file_map:
            raise Exception("File map is empty")
        
        python_files = file_map.get("python_files", [])
        data_files = file_map.get("data_files", [])
        
        print(f"Found {len(python_files)} Python files, {len(data_files)} data files")
        
        # Parse Python files
        python_parser = PythonParser()
        all_functions = []
        all_calls = []
        all_imports = []
        all_data_usage = []
        
        for rel_py_file in python_files:
            full_py_path = os.path.join(repo_path, rel_py_file)
            print(f"🔍 Parsing: {rel_py_file}")
            
            try:
                result = python_parser.parse_file(full_py_path)
                
                # Convert paths with null checks
                for func in result.get("functions", []):
                    if func.get("file"):
                        func["file"] = os.path.relpath(func["file"], repo_path)
                
                for call in result.get("calls", []):
                    if call.get("file"):
                        call["file"] = os.path.relpath(call["file"], repo_path)
                
                for imp in result.get("imports", []):
                    if imp.get("file"):
                        imp["file"] = os.path.relpath(imp["file"], repo_path)
                
                for du in result.get("data_usage", []):
                    if du.get("file"):
                        du["file"] = os.path.relpath(du["file"], repo_path)
                
                all_functions.extend(result.get("functions", []))
                all_calls.extend(result.get("calls", []))
                all_imports.extend(result.get("imports", []))
                all_data_usage.extend(result.get("data_usage", []))
                
            except Exception as e:
                print(f" Error parsing {rel_py_file}: {str(e)}")
                # Continue with other files
                continue
        
        print(f" Collected: {len(all_functions)} functions, {len(all_calls)} calls")
        
        # Resolve imports
        resolver = ImportResolver(repo_path)
        resolved_imports = resolver.resolve_imports(all_imports)
        
        # Build graph
        builder = GraphBuilder()
        builder.add_python_files(python_files)
        builder.add_data_files([{"path": f} for f in data_files])
        builder.add_functions(all_functions)
        builder.add_calls(all_calls)
        builder.add_imports(resolved_imports)
        builder.add_data_usage(all_data_usage)
        
        graph = builder.get_graph()
        
        # Detect issues
        detector = IssueDetector(repo_path)
        issues = detector.run_all_checks(
            graph, 
            all_functions, 
            all_calls, 
            resolved_imports, 
            all_data_usage,
            [{"path": f} for f in data_files]
        )
        
        # NEW: Get AI fixes from Bedrock
        print("Getting AI fixes from Bedrock...")
        bedrock = BedrockHelper()
        ai_fixes = bedrock.generate_fixes(issues, {
            'python_files': len(python_files),
            'functions': len(all_functions),
            'calls': len(all_calls)
        })
        
        # Export graph to JSON
        exporter = GraphExporter(graph)
        graph_json = exporter.export_json_string()
        
        result = {
            'summary': {
                'python_files': len(python_files),
                'data_files': len(data_files),
                'functions': len(all_functions),
                'calls': len(all_calls),
                'imports': len(all_imports),
                'issues': len(issues)
            },
            'issues': issues,
            'ai_fixes': ai_fixes,  # NEW: Add AI fixes to response
            'graph': graph_json,
            'repo_path': repo_path
        }
        
        print(" Analysis complete")
        return result
        
    except Exception as e:
        print(f" Error in analyze_repository: {str(e)}")
        raise e