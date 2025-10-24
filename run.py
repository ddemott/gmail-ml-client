#!/usr/bin/env python3
"""
Gmail ML Client - Main launcher script
Choose how you want to run the application.
"""

import subprocess
import sys
from pathlib import Path


def get_python_executable():
    """Get the Python executable path in a cross-platform way."""
    # Try to find python in virtual environment
    venv_python = Path(".venv/bin/python")  # Linux/Mac
    if venv_python.exists():
        return str(venv_python)

    venv_python_exe = Path(".venv/Scripts/python.exe")  # Windows
    if venv_python_exe.exists():
        return str(venv_python_exe)

    # Fallback to system python
    return sys.executable


def show_menu():
    """Show the main menu."""
    print("=" * 60)
    print("🎯 GMAIL ML CLIENT - LAUNCHER")
    print("=" * 60)
    print()
    print("Choose how you want to run the application:")
    print()
    print("1. 📧 Test Gmail Authentication")
    print("2. 🚀 Start REST API Server (recommended)")
    print("3. 🧪 Run Demo Mode (no Gmail needed)")
    print("4. 🔍 Test Core Functionality")
    print("5. 📊 Run All Tests")
    print("6. 📖 Show Documentation")
    print("7. ❌ Exit")
    print()


def run_command(cmd, description):
    """Run a command with description."""
    print(f"\n🔄 {description}...")
    print(f"Running: {cmd}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, shell=True, check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  {description} interrupted by user")
        return False


def main():
    """Main launcher function."""
    while True:
        show_menu()

        try:
            choice = input("Enter your choice (1-7): ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)

        if choice == "1":
            # Test Gmail Authentication
            python_exe = get_python_executable()
            run_command(
                f'{python_exe} test_gmail_auth.py', "Testing Gmail Authentication"
            )

        elif choice == "2":
            # Start REST API Server
            print("\n🚀 Starting REST API server...")
            print("📍 API will be available at: http://localhost:8000")
            print("📚 API Documentation at: http://localhost:8000/docs")
            print("🔄 Press Ctrl+C to stop the server")
            print("-" * 50)

            try:
                python_exe = get_python_executable()
                subprocess.run(
                    [
                        python_exe,
                        "-m",
                        "uvicorn",
                        "api:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                        "--reload",
                    ]
                )
            except KeyboardInterrupt:
                print("\n⏹️  API server stopped")

        elif choice == "3":
            # Run Demo Mode
            python_exe = get_python_executable()
            run_command(
                f"{python_exe} test_e2e_functionality.py",
                "Running Demo Mode (End-to-End Tests)",
            )

        elif choice == "4":
            # Test Core Functionality
            python_exe = get_python_executable()
            run_command(
                f"{python_exe} test_core_functionality.py",
                "Testing Core Functionality",
            )

        elif choice == "5":
            # Run All Tests
            python_exe = get_python_executable()
            run_command(
                f'{python_exe} -m pytest test_solid.py test_core_functionality.py test_e2e_functionality.py -v',
                "Running All Tests",
            )

        elif choice == "6":
            # Show Documentation
            print("\n📖 Gmail ML Client Documentation")
            print("=" * 40)
            print("📄 README.md - Main documentation")
            print("🔧 API_DOCS.md - REST API reference")
            print("🏗️  ARCHITECTURE.md - System architecture")
            print("📋 CLI_HELP.md - Command line help")
            print("🧪 FINAL_TEST_VALIDATION_REPORT.md - Test results")
            print("\n🌐 Online Documentation:")
            print("   http://localhost:8000/docs (when API server is running)")

        elif choice == "7":
            # Exit
            print("\n👋 Thanks for using Gmail ML Client!")
            break

        else:
            print("\n❌ Invalid choice. Please enter 1-7.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
