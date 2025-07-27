"""Tests for the endpoint serializer module."""

import pytest
import tempfile
from pathlib import Path

from syft_serve._endpoint_serializer import EndpointSerializer


class TestEndpointSerializer:
    """Test the EndpointSerializer class."""

    def test_serializer_initialization(self):
        """Test serializer initialization."""
        serializer = EndpointSerializer()
        assert serializer is not None

    def test_serialize_simple_function(self):
        """Test serializing a simple function."""

        def hello():
            return {"message": "Hello World"}

        endpoints = {"/hello": hello}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert "def hello():" in app_code
        assert 'return {"message": "Hello World"}' in app_code
        assert 'app.get("/hello")' in app_code
        assert "from fastapi import FastAPI" in app_code

    def test_serialize_function_with_parameters(self):
        """Test serializing function with parameters."""

        def echo(message: str):
            return {"echo": message}

        endpoints = {"/echo": echo}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert "def echo(message: str):" in app_code
        assert 'return {"echo": message}' in app_code

    def test_serialize_multiple_endpoints(self):
        """Test serializing multiple endpoints."""

        def hello():
            return {"message": "Hello"}

        def goodbye():
            return {"message": "Goodbye"}

        endpoints = {"/hello": hello, "/goodbye": goodbye}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert "def hello():" in app_code
        assert "def goodbye():" in app_code
        assert 'app.get("/hello")' in app_code
        assert 'app.get("/goodbye")' in app_code

    def test_serialize_lambda_function(self):
        """Test serializing lambda function."""
        endpoints = {"/lambda": lambda: {"result": "lambda"}}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        # Lambda should be called and result stored
        assert "lambda_result_" in app_code or "result" in app_code

    def test_serialize_function_with_closure(self):
        """Test serializing function with closure variables."""
        data = {"value": 42}

        def get_data():
            return data

        endpoints = {"/data": get_data}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        # Should include closure variable
        assert "data = " in app_code
        assert "42" in app_code

    def test_serialize_factory_function(self):
        """Test serializing factory function pattern."""

        def create_handler(file_path):
            def handler():
                with open(file_path, "r") as f:
                    return {"content": f.read()}

            return handler

        # Create a factory function
        file_path = "/tmp/test.txt"
        handler = create_handler(file_path)

        endpoints = {"/file": handler}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        # Should extract closure variables
        assert "file_path" in app_code
        assert "/tmp/test.txt" in app_code

    def test_serialize_with_imports(self):
        """Test serializing function that uses imports."""

        def time_endpoint():
            import time

            return {"timestamp": time.time()}

        endpoints = {"/time": time_endpoint}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert "import time" in app_code
        assert "time.time()" in app_code

    def test_serialize_async_function(self):
        """Test serializing async function."""

        async def async_hello():
            return {"message": "Async Hello"}

        endpoints = {"/async": async_hello}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert "async def async_hello():" in app_code
        assert 'app.get("/async")' in app_code

    def test_serialize_with_docstring(self):
        """Test serializing function with docstring."""

        def documented_function():
            """This function has documentation."""
            return {"status": "documented"}

        endpoints = {"/docs": documented_function}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        assert '"""This function has documentation."""' in app_code

    def test_serialize_error_handling(self):
        """Test serializer error handling."""

        # Function that can't be serialized easily
        def problematic_function():
            # This uses a global that doesn't exist
            return {"value": "undefined"}

        endpoints = {"/problem": problematic_function}
        serializer = EndpointSerializer()

        # Should not raise exception, but handle gracefully
        app_code = serializer.serialize_endpoints(endpoints)
        assert app_code is not None


class TestEndpointSerializerMethods:
    """Test specific methods of EndpointSerializer."""

    def test_extract_function_source(self):
        """Test extracting function source code."""

        def test_function():
            return "test"

        serializer = EndpointSerializer()
        source = serializer._extract_function_source(test_function)

        assert "def test_function():" in source
        assert 'return "test"' in source

    def test_extract_closure_variables(self):
        """Test extracting closure variables."""
        outer_var = "test_value"

        def closure_function():
            return outer_var

        serializer = EndpointSerializer()
        closure_vars = serializer._extract_closure_variables(closure_function)

        assert "outer_var" in closure_vars
        assert closure_vars["outer_var"] == "test_value"

    def test_handle_lambda_function(self):
        """Test handling lambda functions."""

        def multiply_by_two(x):
            return x * 2

        serializer = EndpointSerializer()
        result = serializer._handle_lambda_function(multiply_by_two, "test_lambda")

        # Should return a serializable result
        assert isinstance(result, str)
        assert "test_lambda" in result

    def test_generate_fastapi_app(self):
        """Test generating FastAPI app code."""
        serializer = EndpointSerializer()

        # Mock the function serialization
        function_code = 'def test_func():\n    return "test"'
        endpoint_registrations = 'app.get("/test")(test_func)'

        app_code = serializer._generate_fastapi_app(function_code, endpoint_registrations)

        assert "from fastapi import FastAPI" in app_code
        assert "app = FastAPI()" in app_code
        assert function_code in app_code
        assert endpoint_registrations in app_code


class TestEndpointSerializerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_endpoints(self):
        """Test serializing empty endpoints dictionary."""
        serializer = EndpointSerializer()

        with pytest.raises(ValueError, match="No endpoints provided"):
            serializer.serialize_endpoints({})

    def test_none_endpoints(self):
        """Test serializing None endpoints."""
        serializer = EndpointSerializer()

        with pytest.raises(ValueError, match="Endpoints cannot be None"):
            serializer.serialize_endpoints(None)

    def test_non_callable_endpoint(self):
        """Test with non-callable endpoint."""
        endpoints = {"/test": "not_callable"}
        serializer = EndpointSerializer()

        with pytest.raises(ValueError, match="Endpoint '/test' is not callable"):
            serializer.serialize_endpoints(endpoints)

    def test_invalid_endpoint_path(self):
        """Test with invalid endpoint path."""

        def test_func():
            return "test"

        endpoints = {"invalid_path": test_func}  # Missing leading slash
        serializer = EndpointSerializer()

        with pytest.raises(ValueError, match="Endpoint path must start with '/'"):
            serializer.serialize_endpoints(endpoints)

    def test_function_with_unsupported_features(self):
        """Test function with features that are hard to serialize."""

        # Function using globals
        def uses_global():
            return "test"

        endpoints = {"/global": uses_global}
        serializer = EndpointSerializer()

        # Should handle gracefully
        app_code = serializer.serialize_endpoints(endpoints)
        assert app_code is not None


class TestFileOutput:
    """Test writing serialized code to files."""

    def test_write_to_file(self):
        """Test writing app code to file."""

        def hello():
            return {"message": "Hello"}

        endpoints = {"/hello": hello}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(app_code)
            file_path = f.name

        # Read back and verify
        with open(file_path, "r") as f:
            content = f.read()

        assert "def hello():" in content
        assert "FastAPI" in content

        # Cleanup
        Path(file_path).unlink()

    def test_generated_code_is_valid_python(self):
        """Test that generated code is valid Python."""

        def simple_func():
            return {"status": "ok"}

        endpoints = {"/status": simple_func}
        serializer = EndpointSerializer()

        app_code = serializer.serialize_endpoints(endpoints)

        # Should be valid Python code
        try:
            compile(app_code, "<string>", "exec")
        except SyntaxError:
            pytest.fail("Generated code is not valid Python")


class TestEndpointSerializerIntegration:
    """Integration tests for endpoint serializer."""

    def test_real_world_example(self):
        """Test with a real-world example."""

        # Simulate a data processing endpoint
        def process_data():
            import json

            data = {"processed": True, "count": 42}
            return json.dumps(data)

        # Simulate an ML prediction endpoint
        model_weights = [0.1, 0.2, 0.3]

        def predict():
            # Uses closure variable
            prediction = sum(model_weights)
            return {"prediction": prediction}

        endpoints = {"/process": process_data, "/predict": predict}

        serializer = EndpointSerializer()
        app_code = serializer.serialize_endpoints(endpoints)

        # Verify all components are present
        assert "import json" in app_code
        assert "model_weights = " in app_code
        assert "def process_data():" in app_code
        assert "def predict():" in app_code
        assert 'app.get("/process")' in app_code
        assert 'app.get("/predict")' in app_code
