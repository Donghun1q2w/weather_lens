"""Verification script for API & Scheduler implementation

Run this script to verify all components are correctly implemented.

Usage:
    python verify_implementation.py
"""
import sys
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Expected files and directories
EXPECTED_STRUCTURE = {
    "api": {
        "files": ["__init__.py", "main.py", "README.md"],
        "routes": {
            "files": [
                "__init__.py",
                "health.py",
                "themes.py",
                "regions.py",
                "feedback.py",
                "map.py",
                "internal.py",
            ]
        },
    },
    "files": [
        "main.py",
        "scheduler.py",
        "warmup.py",
        "test_api.py",
        "render.yaml",
        "DEPLOYMENT.md",
        "QUICKSTART.md",
        "API_SCHEDULER_IMPLEMENTATION.md",
    ],
}


def check_file_exists(path: Path) -> bool:
    """Check if file exists and is not empty"""
    return path.exists() and path.is_file() and path.stat().st_size > 0


def check_directory(base: Path, structure: dict, path_prefix: str = "") -> list:
    """Recursively check directory structure"""
    issues = []

    # Check files in current directory
    if "files" in structure:
        for filename in structure["files"]:
            file_path = base / filename
            full_path = f"{path_prefix}/{filename}" if path_prefix else filename

            if not check_file_exists(file_path):
                issues.append(f"Missing or empty file: {full_path}")

    # Check subdirectories
    for key, value in structure.items():
        if key != "files" and isinstance(value, dict):
            subdir = base / key
            if not subdir.exists() or not subdir.is_dir():
                issues.append(f"Missing directory: {path_prefix}/{key}")
            else:
                sub_issues = check_directory(
                    subdir, value, f"{path_prefix}/{key}" if path_prefix else key
                )
                issues.extend(sub_issues)

    return issues


def check_imports():
    """Check if key imports work"""
    import_issues = []

    try:
        import api.main
    except ImportError as e:
        import_issues.append(f"Cannot import api.main: {e}")

    try:
        import scheduler
    except ImportError as e:
        import_issues.append(f"Cannot import scheduler: {e}")

    try:
        from api.routes import (
            health,
            themes,
            regions,
            feedback,
            internal,
        )
    except ImportError as e:
        import_issues.append(f"Cannot import api.routes: {e}")

    try:
        from api.routes import map as map_routes
    except ImportError as e:
        import_issues.append(f"Cannot import api.routes.map: {e}")

    try:
        from fastapi import FastAPI
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from pydantic import BaseModel
    except ImportError as e:
        import_issues.append(f"Missing dependency: {e}")

    return import_issues


def check_config():
    """Check configuration updates"""
    config_issues = []

    try:
        from config.settings import INTERNAL_API_KEY

        if INTERNAL_API_KEY is None:
            config_issues.append("INTERNAL_API_KEY not defined in config.settings")
    except ImportError:
        config_issues.append("Cannot import INTERNAL_API_KEY from config.settings")

    return config_issues


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("PhotoSpot Korea - API & Scheduler Implementation Verification")
    print("=" * 60)
    print()

    all_issues = []

    # Check file structure
    print("Checking file structure...")
    structure_issues = []

    # Check API directory
    api_dir = BASE_DIR / "api"
    if not api_dir.exists():
        structure_issues.append("Missing api/ directory")
    else:
        api_issues = check_directory(api_dir, EXPECTED_STRUCTURE["api"], "api")
        structure_issues.extend(api_issues)

    # Check top-level files
    for filename in EXPECTED_STRUCTURE["files"]:
        file_path = BASE_DIR / filename
        if not check_file_exists(file_path):
            structure_issues.append(f"Missing or empty file: {filename}")

    if structure_issues:
        print(f"  ✗ Found {len(structure_issues)} issues:")
        for issue in structure_issues:
            print(f"    - {issue}")
        all_issues.extend(structure_issues)
    else:
        print("  ✓ All files present")
    print()

    # Check imports
    print("Checking Python imports...")
    import_issues = check_imports()
    if import_issues:
        print(f"  ✗ Found {len(import_issues)} issues:")
        for issue in import_issues:
            print(f"    - {issue}")
        all_issues.extend(import_issues)
    else:
        print("  ✓ All imports successful")
    print()

    # Check configuration
    print("Checking configuration...")
    config_issues = check_config()
    if config_issues:
        print(f"  ✗ Found {len(config_issues)} issues:")
        for issue in config_issues:
            print(f"    - {issue}")
        all_issues.extend(config_issues)
    else:
        print("  ✓ Configuration correct")
    print()

    # Summary
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)

    if all_issues:
        print(f"✗ Found {len(all_issues)} issues")
        print("\nPlease fix the issues above before deployment.")
        return 1
    else:
        print("✓ All checks passed!")
        print("\nNext steps:")
        print("1. Run the application: python main.py")
        print("2. Run tests: python test_api.py")
        print("3. View API docs: http://localhost:8000/docs")
        print("4. Deploy to Render (see DEPLOYMENT.md)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
