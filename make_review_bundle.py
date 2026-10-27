import os
import zipfile

BUNDLE_NAME = "review_bundle.zip"

INCLUDE_DIRS = ["core", "data", "tests", "docs"]
INCLUDE_FILES = [
    "app.py",
    "requirements.txt",
    "pytest.ini",
    "README.md",
    "run.bat",
    "capture_verification_screens.py"
]

def create_bundle():
    if os.path.exists(BUNDLE_NAME):
        os.remove(BUNDLE_NAME)

    with zipfile.ZipFile(BUNDLE_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Include explicit top-level files
        for f in INCLUDE_FILES:
            if os.path.isfile(f):
                zipf.write(f, arcname=f)
                print(f"Added file: {f}")

        # Include specific directories
        for folder in INCLUDE_DIRS:
            for root, dirs, files in os.walk(folder):
                # Exclude cache directories
                dirs[:] = [d for d in dirs if d not in ["__pycache__", ".pytest_cache", ".git"]]
                for file in files:
                    if file.endswith((".pyc", ".pyo")):
                        continue
                    full_path = os.path.join(root, file)
                    arc_path = os.path.relpath(full_path, start=".")
                    zipf.write(full_path, arcname=arc_path)
                    print(f"Added: {arc_path}")

    # Verify integrity with testzip
    with zipfile.ZipFile(BUNDLE_NAME, "r") as z:
        bad_file = z.testzip()
        if bad_file:
            raise RuntimeError(f"Zip integrity test failed on {bad_file}")
        file_count = len(z.namelist())
        size_bytes = os.path.getsize(BUNDLE_NAME)
        size_mb = size_bytes / (1024 * 1024)

    print("\n--- ZIP VERIFICATION REPORT ---")
    print(f"Archive: {os.path.abspath(BUNDLE_NAME)}")
    print(f"Status: VALID (testzip() returned None)")
    print(f"Total entries: {file_count}")
    print(f"File size: {size_bytes} bytes ({size_mb:.2f} MB)")

if __name__ == "__main__":
    create_bundle()
