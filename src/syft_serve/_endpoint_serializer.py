"""
Utilities for serializing endpoint functions to Python code
"""

import inspect
import textwrap
import pickle
import base64
from typing import Callable, Dict


def serialize_endpoint_function(func: Callable, func_name: str) -> str:
    """
    Serialize a function to Python code.
    
    For simple functions, we can use inspect.getsource().
    For lambdas and complex functions, we pickle them.
    For closures, we try to extract closure variables.
    """
    try:
        # Try to get the source code
        source = inspect.getsource(func)
        
        # Handle lambdas specially
        if 'lambda' in source and source.strip().startswith('lambda'):
            # It's a one-line lambda, we can't use getsource properly
            raise TypeError("Lambda function")
            
        # Check if it's a closure (has free variables)
        closure_vars = {}
        if func.__closure__:
            # Extract closure variables
            for i, cell in enumerate(func.__closure__):
                var_name = func.__code__.co_freevars[i]
                try:
                    var_value = cell.cell_contents
                    # Only capture simple types that can be serialized
                    if isinstance(var_value, (str, int, float, bool, list, dict, type(None))):
                        closure_vars[var_name] = var_value
                    elif hasattr(var_value, '__dict__'):
                        # Try to capture simple object attributes
                        simple_attrs = {}
                        for attr, val in var_value.__dict__.items():
                            if isinstance(val, (str, int, float, bool, list, dict)):
                                simple_attrs[attr] = val
                        if simple_attrs:
                            closure_vars[var_name] = simple_attrs
                except:
                    pass
            
        # Remove any decorators and fix indentation
        lines = source.split('\n')
        
        # Find the first def line
        def_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                def_index = i
                break
        
        if def_index >= 0:
            # Get the function definition
            func_lines = lines[def_index:]
            
            # Remove common leading whitespace
            min_indent = float('inf')
            for line in func_lines:
                if line.strip():  # Skip empty lines
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)
            
            # Remove the common indent
            dedented_lines = []
            for line in func_lines:
                if line.strip():
                    dedented_lines.append(line[min_indent:])
                else:
                    dedented_lines.append('')
            
            # Replace function name
            first_line = dedented_lines[0]
            if 'def ' in first_line:
                # Extract everything after 'def ' and before '('
                import re
                first_line = re.sub(r'def\s+\w+\s*\(', f'def {func_name}(', first_line)
                dedented_lines[0] = first_line
            
            # If we have closure variables, inject them at the beginning of the function
            if closure_vars:
                # Add variable definitions after the function signature
                var_lines = []
                for var_name, var_value in closure_vars.items():
                    if isinstance(var_value, str):
                        var_lines.append(f"    {var_name} = {repr(var_value)}")
                    else:
                        var_lines.append(f"    {var_name} = {var_value}")
                
                # Insert after the def line
                dedented_lines = [dedented_lines[0]] + var_lines + dedented_lines[1:]
            
            return '\n'.join(dedented_lines)
        else:
            raise TypeError("Could not find function definition")
            
    except (OSError, TypeError, IOError):
        # Can't get source - for lambdas, try to extract the return value
        func_str = str(func)
        
        # Check if it's a lambda
        if '<lambda>' in func_str:
            # Try to call it and see what it returns
            try:
                result = func()
                # If it returns a dict/list/primitive, we can generate code for it
                import json
                json_result = json.dumps(result)
                return f'''def {func_name}():
    # Auto-generated from lambda function
    return {json_result}'''
            except:
                pass
        
        # Fallback: generic endpoint
        return f'''def {func_name}():
    # Auto-generated wrapper for {func_str}
    return {{"message": "Auto-generated endpoint", "path": "{func_name}"}}'''


def generate_app_code_from_endpoints(endpoints: Dict[str, Callable], name: str) -> str:
    """Generate complete FastAPI app code from endpoints dictionary"""
    
    # Serialize all endpoint functions
    endpoint_functions = []
    for path, func in endpoints.items():
        # Create a safe function name from the path
        import re
        route_func_name = "endpoint_" + re.sub(r'[^a-zA-Z0-9_]', '_', path.strip('/'))
        if not route_func_name or route_func_name == "endpoint_":
            route_func_name = "endpoint_root"
        
        func_code = serialize_endpoint_function(func, route_func_name)
        
        endpoint_functions.append({
            'path': path,
            'func_name': route_func_name,
            'func_code': func_code
        })
    
    # Generate the complete app code
    app_code = f'''"""
Auto-generated FastAPI app for {name}
Created by SyftServe with isolated environment
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import time

# Create app without automatic docs to avoid conflicts
app = FastAPI(
    title="{name}",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
def health():
    return {{"status": "ok", "service": "syft-serve", "name": "{name}"}}

# Endpoint hash for compatibility checking
@app.get("/api/hash")
def get_endpoint_hash():
    endpoints = {list(endpoints.keys())}
    sorted_endpoints = sorted(endpoints)
    hash_string = str(sorted_endpoints)
    endpoint_hash = hashlib.md5(hash_string.encode()).hexdigest()
    return {{
        "hash": endpoint_hash,
        "endpoints": sorted_endpoints,
        "count": len(sorted_endpoints)
    }}

# Server info endpoint for process discovery
@app.get("/syft/info")
def get_server_info():
    import os
    import datetime
    return {{
        "name": "{name}",
        "service": "syft-serve",
        "pid": os.getpid(),
        "start_time": datetime.datetime.now().isoformat(),
        "endpoints": {list(endpoints.keys())},
        "endpoint_hash": get_endpoint_hash()["hash"],
        "version": "0.1.0"
    }}

# User-defined endpoint functions
'''
    
    # Add the endpoint functions
    for ep in endpoint_functions:
        app_code += f"\n{ep['func_code']}\n"
    
    # Add the routes
    app_code += "\n# Register routes\n"
    for ep in endpoint_functions:
        app_code += f'app.add_api_route("{ep["path"]}", {ep["func_name"]}, methods=["GET"])\n'
    
    return app_code