"""Setup script for the Multi-Agent Mechanic Workflow."""

from pathlib import Path
import subprocess
import sys


def check_python_version():
    """Check if Python version is 3.9 or higher."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"Python version: {sys.version.split()[0]}")
    return True


def create_directories():
    """Create necessary directories."""
    directories = ["data/users", "data/chroma_db", "output"]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    print("Created necessary directories")


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")

    if not env_path.exists():
        if env_example_path.exists():
            print(".env file not found")
            print("   Please copy .env.example to .env and add your API keys:")
            print("   cp .env.example .env")
            return False
        else:
            print(".env.example file not found")
            return False

    print(".env file exists")
    return True


def install_dependencies():
    """Install required dependencies."""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Error installing dependencies")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Multi-Agent Mechanic Workflow - Setup")
    print("=" * 60)
    print()

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Create directories
    create_directories()

    # Install dependencies
    # if not install_dependencies():
    # sys.exit(1)

    # Check .env file
    env_exists = check_env_file()

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)

    if not env_exists:
        print()
        print("Next Steps:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("2. Edit .env and add your API keys")
        print("3. Run the system:")
        print("   python src/main.py")
    else:
        print()
        print("Ready to use!")
        print()
        print("Run the system:")
        print("  python src/main.py")
        print()
        print("Run tests:")
        print("  python tests/test_workflow.py")

    print()
    """Setuptools entrypoint for editable and wheel builds."""

    from setuptools import find_packages, setup

    setup(
        packages=find_packages(where="src"),
        package_dir={"": "src"},
    )


if __name__ == "__main__":
    main()
