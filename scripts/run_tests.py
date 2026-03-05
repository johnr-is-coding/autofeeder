import subprocess
import sys
import tomllib
from pathlib import Path


def get_test_dir() -> Path:
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    try:
        test_path = config["tool"]["pytest"]["ini_options"]["testpaths"][0]
    except (KeyError, IndexError):
        print("❌ Could not find testpaths in pyproject.toml")
        sys.exit(1)

    return Path(test_path)


def find_test_file(test_dir: Path, name: str) -> Path | None:
    return next(test_dir.rglob(f"test_{name}.py"), None)


def find_test_folder(test_dir: Path, name: str) -> Path | None:
    for candidate in test_dir.rglob(name):
        if candidate.is_dir():
            return candidate
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: poetry run test <file_name|folder_name>")
        sys.exit(1)

    test_dir = get_test_dir()
    arg = sys.argv[1]

    test_folder = find_test_folder(test_dir, arg)
    if test_folder:
        print(f"✅ Running all tests in folder: {test_folder}")
        target = str(test_folder)
    else:
        test_file = find_test_file(test_dir, arg)
        if not test_file:
            print(f"❌ No matching test file or folder found for '{arg}'")
            sys.exit(1)
        print(f"✅ Running tests: {test_file}")
        target = str(test_file)

    try:
        subprocess.run(
            ["poetry", "run", "pytest", "-vv", target],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        sys.exit(e.returncode)