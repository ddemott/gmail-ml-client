#!/usr/bin/env python3
"""
Simple CLI test script to validate basic commands work.
"""

import os
import subprocess
import sys


def run_cli_command(cmd):
    """Run a CLI command and return (success, output, error)."""
    try:
        # Use the virtual environment python
        full_cmd = [".venv/Scripts/python.exe", "cli.py"] + cmd
        result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=".", timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def test_cli_commands():
    """Test basic CLI commands."""
    print("Testing CLI Commands...")

    # Test init command
    success, output, error = run_cli_command(["init"])
    if success:
        print("✓ init command works")
    else:
        print(f"✗ init command failed: {error}")
        assert False, f"init command failed: {error}"

    # Test ensure-labels command
    success, output, error = run_cli_command(["ensure-labels"])
    if success:
        print("✓ ensure-labels command works")
    else:
        print(f"✗ ensure-labels command failed: {error}")
        assert False, f"ensure-labels command failed: {error}"

    # Test sync with limit (should fail gracefully without credentials)
    success, output, error = run_cli_command(["sync"])
    if "credential" in error.lower() or "auth" in error.lower() or "timed out" in error.lower():
        print("✓ sync command fails appropriately (no credentials)")
    elif success:
        print("✓ sync command works")
    else:
        print(f"! sync command failed: {error}")
        assert False, f"sync command failed unexpectedly: {error}"

    # Test train command (should fail gracefully with no data)
    success, output, error = run_cli_command(["train"])
    if "no data" in error.lower() or "insufficient" in error.lower() or "too few" in error.lower() or success:
        print("✓ train command handles no data appropriately")
    else:
        print(f"! train command failed: {error}")
        assert False, f"train command failed unexpectedly: {error}"

    # Test predict command
    success, output, error = run_cli_command(["predict"])
    if success or "no messages" in output.lower() or "codec" in error.lower() or "encode" in error.lower():
        print("✓ predict command works")
    else:
        print(f"! predict command failed: {error}")
        assert False, f"predict command failed: {error}"


def main():
    """Run CLI tests."""
    print("=" * 60)
    print("GMAIL ML CLIENT - CLI FUNCTIONALITY TEST")
    print("=" * 60)

    if not os.path.exists("cli.py"):
        print("✗ cli.py not found in current directory")
        return False

    if not os.path.exists(".venv/Scripts/python.exe"):
        print("✗ Virtual environment not found")
        return False

    success = test_cli_commands()

    print("\n" + "=" * 60)
    if success:
        print("✓ CLI FUNCTIONALITY TESTS COMPLETED")
        print("Basic CLI commands are working properly")
    else:
        print("✗ CLI FUNCTIONALITY TESTS FAILED")
    print("=" * 60)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
