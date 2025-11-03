"""Debug script for GCS filesystem access and path configuration.

Tests:
1. GCS authentication and bucket access
2. File listing with different path formats
3. Path mapping from config to GCS
4. Comparison with gcloud CLI output
"""

import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage

# Load environment
load_dotenv()

# NOTE: Bucket name is "athena-enterprise", path inside bucket is just company/workspace
COMPANY_SLUG = "acme-corp"
WORKSPACE_SLUG = "cliente-1"


def print_section(title):
    """Print formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def test_environment_variables():
    """Test that required environment variables are set."""
    print_section("1. Environment Variables")

    bucket_name = os.getenv("GCS_BUCKET_NAME")
    credentials_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")

    print(f"GCS_BUCKET_NAME: {bucket_name or 'NOT SET'}")
    print(f"GOOGLE_CLOUD_CREDENTIALS_JSON: {'SET' if credentials_json else 'NOT SET'}")

    if credentials_json:
        try:
            creds = json.loads(credentials_json)
            print(f"  - type: {creds.get('type')}")
            print(f"  - project_id: {creds.get('project_id')}")
            print(f"  - client_email: {creds.get('client_email')}")
        except json.JSONDecodeError as e:
            print(f"  ERROR parsing JSON: {e}")

    return bucket_name, credentials_json


def test_gcs_authentication(bucket_name):
    """Test GCS client authentication and bucket access."""
    print_section("2. GCS Authentication & Bucket Access")

    try:
        from src.agent.tools.shared.gcs.client import get_gcs_client

        client = get_gcs_client()
        print(f"✅ GCS client initialized")
        print(f"   Project: {client.project}")

        bucket = client.bucket(bucket_name)
        exists = bucket.exists()
        print(f"✅ Bucket '{bucket_name}' exists: {exists}")

        if not exists:
            print(f"❌ Bucket not found or no access")
            return None

        return bucket

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_path_construction():
    """Test path construction from config."""
    print_section("3. Path Construction")

    # Path built by ConfigToStateMiddleware (inside bucket)
    gcs_root_path = f"{COMPANY_SLUG}/{WORKSPACE_SLUG}/"

    print(f"Bucket name: athena-enterprise")
    print(f"Company slug: {COMPANY_SLUG}")
    print(f"Workspace slug: {WORKSPACE_SLUG}")
    print(f"GCS root path (inside bucket): {gcs_root_path}")
    print(f"Full GCS URL: gs://athena-enterprise/{gcs_root_path}")

    return gcs_root_path


def test_list_bucket_root(bucket):
    """List all items in bucket root to understand structure."""
    print_section("4. Bucket Root Contents")

    try:
        print("Listing top-level prefixes (directories) in bucket...")

        blobs = list(bucket.list_blobs(delimiter="/", max_results=50))
        prefixes = list(bucket.list_blobs(delimiter="/", max_results=1).prefixes)

        print(f"\nTop-level directories ({len(prefixes)}):")
        for prefix in prefixes:
            print(f"  - {prefix}")

        print(f"\nTop-level files ({len(blobs)}):")
        for blob in blobs[:10]:
            print(f"  - {blob.name}")

        if len(blobs) > 10:
            print(f"  ... and {len(blobs) - 10} more files")

        return prefixes

    except Exception as e:
        print(f"❌ Error listing bucket: {e}")
        return []


def test_list_with_gcs_path(bucket, gcs_root_path):
    """Test listing with the exact path built by middleware."""
    print_section("5. List Files with Configured Path")

    # Remove trailing slash for prefix
    prefix = gcs_root_path.rstrip("/")

    print(f"Testing prefix: '{prefix}'")
    print(f"With delimiter: '/'")

    try:
        # Test with exact prefix
        print(f"\n📁 Listing: {prefix}/")
        iterator = bucket.list_blobs(prefix=prefix + "/", delimiter="/", max_results=100)

        files = []
        directories = []

        for blob in iterator:
            files.append(blob.name)

        for p in iterator.prefixes:
            directories.append(p)

        print(f"\nDirectories found ({len(directories)}):")
        for d in directories:
            print(f"  📁 {d}")

        print(f"\nFiles found ({len(files)}):")
        for f in files[:20]:
            print(f"  📄 {f}")

        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more files")

        if not files and not directories:
            print("⚠️  No files or directories found!")
            print("\nTrying parent paths...")

            # Try without workspace
            parent_prefix = f"{COMPANY_SLUG}/"
            print(f"\n📁 Listing parent: {parent_prefix}")
            parent_iter = bucket.list_blobs(prefix=parent_prefix, delimiter="/", max_results=10)
            parent_prefixes = list(parent_iter.prefixes)

            print(f"Found {len(parent_prefixes)} items:")
            for p in parent_prefixes:
                print(f"  - {p}")

        return files, directories

    except Exception as e:
        print(f"❌ Error: {e}")
        return [], []


def test_list_company_workspaces(bucket):
    """List all workspaces under company to find actual structure."""
    print_section("6. Explore Company Workspaces")

    company_prefix = f"{COMPANY_SLUG}/"
    print(f"Listing workspaces for company: {company_prefix}")

    try:
        iterator = bucket.list_blobs(prefix=company_prefix, delimiter="/", max_results=50)
        workspaces = list(iterator.prefixes)

        print(f"\nWorkspaces found ({len(workspaces)}):")
        for ws in workspaces:
            print(f"  - {ws}")

            # List files in each workspace
            ws_iter = bucket.list_blobs(prefix=ws, delimiter="/", max_results=5)
            ws_files = list(ws_iter)
            ws_dirs = list(ws_iter.prefixes)

            print(f"    Files: {len(ws_files)}, Directories: {len(ws_dirs)}")
            for f in ws_files[:3]:
                print(f"      📄 {f.name}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_gcloud_cli():
    """Test with gcloud CLI to see actual structure."""
    print_section("7. Verification with gcloud CLI")

    bucket_name = os.getenv("GCS_BUCKET_NAME")

    commands = [
        # List bucket root
        f"gcloud storage ls gs://{bucket_name}/",
        # List company
        f"gcloud storage ls gs://{bucket_name}/{COMPANY_SLUG}/",
        # List workspace
        f"gcloud storage ls gs://{bucket_name}/{COMPANY_SLUG}/{WORKSPACE_SLUG}/",
        # Recursive list to see all files
        f"gcloud storage ls -r gs://{bucket_name}/{COMPANY_SLUG}/ | head -20",
    ]

    for cmd in commands:
        print(f"\n$ {cmd}")
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    lines = output.split('\n')
                    print(f"✅ Found {len(lines)} items:")
                    for line in lines[:10]:
                        print(f"   {line}")
                    if len(lines) > 10:
                        print(f"   ... and {len(lines) - 10} more")
                else:
                    print("⚠️  Empty (no files/directories)")
            else:
                print(f"❌ Error (code {result.returncode}):")
                print(f"   {result.stderr.strip()}")

        except subprocess.TimeoutExpired:
            print("❌ Command timed out")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_path_validation():
    """Test path validation logic."""
    print_section("8. Path Validation Tests")

    from src.agent.tools.shared.gcs.validation import validate_path, validate_root_path

    gcs_root_path = f"{COMPANY_SLUG}/{WORKSPACE_SLUG}/"

    print(f"Root path: {gcs_root_path}")

    try:
        validate_root_path(gcs_root_path)
        print("✅ Root path validation passed")
    except Exception as e:
        print(f"❌ Root path validation failed: {e}")
        return

    # Test various file paths
    test_paths = [
        "/",
        "file.txt",
        "/file.txt",
        "subdir/file.txt",
        "/subdir/file.txt",
        "../etc/passwd",  # Should fail
    ]

    print("\nTesting file path validation:")
    for path in test_paths:
        try:
            result = validate_path(path, gcs_root_path)
            print(f"  ✅ '{path}' -> '{result}'")
        except Exception as e:
            print(f"  ❌ '{path}' -> Error: {e}")

    # Test that directories match what we found
    print("\nExpected paths match found directories:")
    expected_dirs = [
        "documentazione_tecnica/",
        "fattura/",
        "fattura_servizi_idrici/",
        "ricerca_scientifica/",
    ]
    for d in expected_dirs:
        try:
            result = validate_path(d, gcs_root_path)
            print(f"  ✅ '{d}' -> '{result}'")
        except Exception as e:
            print(f"  ❌ '{d}' -> Error: {e}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  GCS FILESYSTEM DEBUG SCRIPT")
    print("=" * 80)

    # Test 1: Environment
    bucket_name, credentials_json = test_environment_variables()

    if not bucket_name or not credentials_json:
        print("\n❌ Missing required environment variables. Set in .env:")
        print("   GCS_BUCKET_NAME='your-bucket'")
        print("   GOOGLE_CLOUD_CREDENTIALS_JSON='{...}'")
        return

    # Test 2: Authentication
    bucket = test_gcs_authentication(bucket_name)

    if not bucket:
        print("\n❌ Cannot access GCS bucket. Check credentials and permissions.")
        return

    # Test 3: Path construction
    gcs_root_path = test_path_construction()

    # Test 4: List bucket root
    top_level_dirs = test_list_bucket_root(bucket)

    # Test 5: List with configured path
    files, directories = test_list_with_gcs_path(bucket, gcs_root_path)

    # Test 6: Explore company workspaces
    test_list_company_workspaces(bucket)

    # Test 7: gcloud CLI
    test_gcloud_cli()

    # Test 8: Path validation
    test_path_validation()

    # Summary
    print_section("SUMMARY")
    print(f"Bucket: {bucket_name}")
    print(f"GCS Path: {gcs_root_path}")
    print(f"Files found: {len(files)}")
    print(f"Directories found: {len(directories)}")

    if files or directories:
        print("\n✅ GCS access is working! Agent should be able to see files.")
    else:
        print("\n⚠️  No files found at configured path.")
        print("   Check:")
        print("   1. Files exist in bucket at this path")
        print("   2. Service account has read permissions")
        print("   3. Path mapping is correct (company_slug, workspace_slug)")


if __name__ == "__main__":
    main()
