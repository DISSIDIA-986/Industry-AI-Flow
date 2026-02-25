"""BUG-1 (Critical): DockerExecutor.execute() never calls _validate_code().

The `DockerExecutor.execute()` method accepts arbitrary code and runs it in
a Docker container WITHOUT calling the `_validate_code()` security validator.
The validator exists as a method on the class but is dead code — no path in
`execute()` or `execute_code()` invokes it.

This test asserts that code IS validated before execution.  It should FAIL
until the bug is fixed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBug1DockerValidationNotCalled:

    def test_execute_calls_validate_code_before_running(self):
        """execute() must invoke _validate_code() and reject blocked code."""
        # Arrange: create a DockerExecutor with mocked Docker client
        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.images.get.return_value = MagicMock()  # image exists

            from backend.services.code_executor.docker_executor import DockerExecutor

            executor = DockerExecutor()

            # Dangerous code that should be rejected by the validator
            dangerous_code = "import os; os.system('rm -rf /')"

            result = executor.execute(dangerous_code)

            # Assert: execution should have been blocked by validation
            assert not result.success, (
                "BUG-1: DockerExecutor.execute() ran dangerous code without "
                "calling _validate_code(). The validator is dead code."
            )
            assert result.error is not None, (
                "BUG-1: Expected a validation error message when blocked code "
                "is submitted to execute()"
            )

    def test_execute_code_calls_validate_code_before_running(self):
        """execute_code() must also invoke validation before running."""
        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.images.get.return_value = MagicMock()

            from backend.services.code_executor.docker_executor import DockerExecutor

            executor = DockerExecutor()

            dangerous_code = "import subprocess; subprocess.run(['ls'])"

            result = executor.execute_code(dangerous_code)

            assert not result["success"], (
                "BUG-1: execute_code() ran dangerous code without validation"
            )
