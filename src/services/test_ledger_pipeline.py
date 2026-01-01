"""
OmniTrust Ledger Pipeline Test Script
Tests the complete pipeline: upload → monitor → hash → verify

This script:
1. Uploads test files to the 'omnitrust-raw-media' container
2. Runs the ledger monitor to process new files
3. Verifies hashes are correctly stored in the ledger
4. Tests hash verification functionality
5. Demonstrates the complete workflow

Usage:
    python src/services/test_ledger_pipeline.py
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError

from src.services.ledger import (
    LedgerMonitorService,
    get_connection_string
)


def create_test_file(content: str, prefix: str = "pipeline_test") -> str:
    """
    Create a temporary test file.
    
    Args:
        content: Content to write to the file.
        prefix: Prefix for the temporary filename.
    
    Returns:
        Path to the temporary file.
    """
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        prefix=f"{prefix}_",
        suffix='.txt',
        delete=False
    )
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def upload_test_file_to_blob(
    blob_service_client: BlobServiceClient,
    container_name: str,
    file_path: str,
    blob_name: str
) -> str:
    """
    Upload a file to blob storage.
    
    Args:
        blob_service_client: BlobServiceClient instance.
        container_name: Name of the container.
        file_path: Local path to the file to upload.
        blob_name: Name for the blob in storage.
    
    Returns:
        The blob name.
    """
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(file_path, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        
        print(f"  [OK] Uploaded: {blob_name}")
        return blob_name
    except HttpResponseError as e:
        print(f"  [ERROR] Failed to upload {blob_name}: {e}")
        raise


def test_upload_phase(blob_service_client: BlobServiceClient, container_name: str) -> List[str]:
    """
    Test Phase 1: Upload test files to blob storage.
    
    Args:
        blob_service_client: BlobServiceClient instance.
        container_name: Name of the container.
    
    Returns:
        List of uploaded blob names.
    """
    print("\n" + "=" * 60)
    print("Phase 1: Upload Test Files to Blob Storage")
    print("=" * 60)
    
    uploaded_blobs = []
    test_files = [
        {
            "content": f"""OmniTrust Pipeline Test File 1
Created: {datetime.now(timezone.utc).isoformat()}
Purpose: Testing ledger monitoring pipeline
Content: This is test file 1 for pipeline verification.
""",
            "blob_name": f"pipeline_test/file1_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
        },
        {
            "content": f"""OmniTrust Pipeline Test File 2
Created: {datetime.now(timezone.utc).isoformat()}
Purpose: Testing ledger monitoring pipeline
Content: This is test file 2 with different content for verification.
Additional data: Test data for hash computation.
""",
            "blob_name": f"pipeline_test/file2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
        }
    ]
    
    temp_files = []
    try:
        for test_file in test_files:
            # Create temporary file
            temp_path = create_test_file(test_file["content"])
            temp_files.append(temp_path)
            
            # Upload to blob storage
            blob_name = upload_test_file_to_blob(
                blob_service_client,
                container_name,
                temp_path,
                test_file["blob_name"]
            )
            uploaded_blobs.append(blob_name)
        
        print(f"\n[SUCCESS] Uploaded {len(uploaded_blobs)} test file(s)")
        return uploaded_blobs
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except OSError:
                pass


def test_monitor_phase(container_name: str, ledger_file: str) -> Dict[str, Any]:
    """
    Test Phase 2: Monitor container and process new files.
    
    Args:
        container_name: Name of the container to monitor.
        ledger_file: Path to the ledger file.
    
    Returns:
        Dictionary with monitoring results.
    """
    print("\n" + "=" * 60)
    print("Phase 2: Monitor Container and Process Files")
    print("=" * 60)
    
    # Get initial stats
    service = LedgerMonitorService(
        container_name=container_name,
        ledger_file=ledger_file
    )
    initial_stats = service.get_ledger_stats()
    print(f"\nInitial ledger state:")
    print(f"  Total entries: {initial_stats['total_entries']}")
    print(f"  Processed blobs: {initial_stats['processed_blobs']}")
    
    # Monitor and process
    print(f"\nMonitoring container '{container_name}'...")
    results = service.monitor_and_process()
    
    # Get updated stats
    updated_stats = service.get_ledger_stats()
    print(f"\nUpdated ledger state:")
    print(f"  Total entries: {updated_stats['total_entries']}")
    print(f"  Processed blobs: {updated_stats['processed_blobs']}")
    
    return {
        "initial_stats": initial_stats,
        "updated_stats": updated_stats,
        "processing_results": results,
        "service": service
    }


def test_verification_phase(
    service: LedgerMonitorService,
    blob_service_client: BlobServiceClient,
    container_name: str
) -> Dict[str, Any]:
    """
    Test Phase 3: Verify hash integrity.
    
    Args:
        service: LedgerMonitorService instance.
        blob_service_client: BlobServiceClient instance.
        container_name: Name of the container.
    
    Returns:
        Dictionary with verification results.
    """
    print("\n" + "=" * 60)
    print("Phase 3: Hash Verification")
    print("=" * 60)
    
    verification_results = []
    
    # Get some entries from the ledger
    stats = service.get_ledger_stats()
    if stats['total_entries'] == 0:
        print("\n[WARNING] No entries in ledger to verify")
        return {"verification_results": []}
    
    # Load ledger to get entries
    ledger_path = Path(service.ledger_file)
    with open(ledger_path, 'r', encoding='utf-8') as f:
        ledger_data = json.load(f)
    
    # Verify first few entries
    entries_to_verify = ledger_data.get("entries", [])[-2:]  # Last 2 entries
    
    for entry in entries_to_verify:
        hash_value = entry.get("hash")
        blob_name = entry.get("blob_name")
        transaction_id = entry.get("transaction_id")
        
        print(f"\nVerifying hash for: {blob_name}")
        print(f"  Transaction ID: {transaction_id}")
        print(f"  Hash: {hash_value[:32]}...")
        
        # Verify using ledger service
        verification = service.verify_hash(hash_value)
        
        if verification.get("verified"):
            print(f"  [OK] Hash verified successfully")
            verification_results.append({
                "blob_name": blob_name,
                "hash": hash_value,
                "verified": True,
                "transaction_id": transaction_id
            })
        else:
            print(f"  [ERROR] Hash verification failed")
            verification_results.append({
                "blob_name": blob_name,
                "hash": hash_value,
                "verified": False
            })
    
    # Test with invalid hash
    print(f"\nTesting with invalid hash...")
    invalid_verification = service.verify_hash("invalid_hash_12345")
    if not invalid_verification.get("verified"):
        print(f"  [OK] Invalid hash correctly rejected")
    else:
        print(f"  [ERROR] Invalid hash incorrectly accepted")
    
    return {"verification_results": verification_results}


def test_integrity_check(
    service: LedgerMonitorService,
    blob_service_client: BlobServiceClient,
    container_name: str
) -> Dict[str, Any]:
    """
    Test Phase 4: Integrity check - recompute hash and compare.
    
    Args:
        service: LedgerMonitorService instance.
        blob_service_client: BlobServiceClient instance.
        container_name: Name of the container.
    
    Returns:
        Dictionary with integrity check results.
    """
    print("\n" + "=" * 60)
    print("Phase 4: Integrity Check (Recompute Hash)")
    print("=" * 60)
    
    integrity_results = []
    
    # Load ledger to get entries
    ledger_path = Path(service.ledger_file)
    with open(ledger_path, 'r', encoding='utf-8') as f:
        ledger_data = json.load(f)
    
    # Check integrity of last entry
    entries = ledger_data.get("entries", [])
    if not entries:
        print("\n[WARNING] No entries in ledger for integrity check")
        return {"integrity_results": []}
    
    entry = entries[-1]  # Get last entry
    blob_name = entry.get("blob_name")
    stored_hash = entry.get("hash")
    
    print(f"\nChecking integrity of: {blob_name}")
    print(f"  Stored hash: {stored_hash[:32]}...")
    
    try:
        # Download blob from storage
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()
        
        # Recompute hash
        recomputed_hash = LedgerMonitorService.compute_sha256(blob_data)
        print(f"  Recomputed hash: {recomputed_hash[:32]}...")
        
        # Compare
        if stored_hash == recomputed_hash:
            print(f"  [OK] Integrity check passed - hashes match!")
            integrity_results.append({
                "blob_name": blob_name,
                "integrity_verified": True,
                "stored_hash": stored_hash,
                "recomputed_hash": recomputed_hash
            })
        else:
            print(f"  [ERROR] Integrity check failed - hashes don't match!")
            integrity_results.append({
                "blob_name": blob_name,
                "integrity_verified": False,
                "stored_hash": stored_hash,
                "recomputed_hash": recomputed_hash
            })
    except Exception as e:
        print(f"  [ERROR] Failed to perform integrity check: {e}")
        integrity_results.append({
            "blob_name": blob_name,
            "integrity_verified": False,
            "error": str(e)
        })
    
    return {"integrity_results": integrity_results}


def main():
    """Main test function."""
    print("=" * 60)
    print("OmniTrust Ledger Pipeline Test")
    print("=" * 60)
    
    # Configuration
    CONTAINER_NAME = "omnitrust-raw-media"
    LEDGER_FILE = "mock_ledger.json"
    
    test_results = {
        "upload_phase": None,
        "monitor_phase": None,
        "verification_phase": None,
        "integrity_phase": None,
        "success": False
    }
    
    try:
        # Initialize blob service client
        connection_string = get_connection_string()
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Verify container exists
        try:
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)
            container_client.get_container_properties()
        except HttpResponseError:
            print(f"\n[ERROR] Container '{CONTAINER_NAME}' does not exist!")
            print("Please run test_storage.py first to create the container.")
            return 1
        
        # Phase 1: Upload test files
        uploaded_blobs = test_upload_phase(blob_service_client, CONTAINER_NAME)
        test_results["upload_phase"] = {"uploaded_blobs": uploaded_blobs}
        
        # Phase 2: Monitor and process
        monitor_results = test_monitor_phase(CONTAINER_NAME, LEDGER_FILE)
        test_results["monitor_phase"] = monitor_results
        service = monitor_results["service"]
        
        # Phase 3: Verify hashes
        verification_results = test_verification_phase(
            service,
            blob_service_client,
            CONTAINER_NAME
        )
        test_results["verification_phase"] = verification_results
        
        # Phase 4: Integrity check
        integrity_results = test_integrity_check(
            service,
            blob_service_client,
            CONTAINER_NAME
        )
        test_results["integrity_phase"] = integrity_results
        
        # Final summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"\nUpload Phase: {'PASSED' if uploaded_blobs else 'FAILED'}")
        print(f"  Uploaded {len(uploaded_blobs)} file(s)")
        
        processing_results = monitor_results.get("processing_results", [])
        print(f"\nMonitor Phase: {'PASSED' if processing_results else 'FAILED'}")
        print(f"  Processed {len(processing_results)} file(s)")
        
        verification_results_list = verification_results.get("verification_results", [])
        verified_count = sum(1 for r in verification_results_list if r.get("verified"))
        print(f"\nVerification Phase: {'PASSED' if verified_count == len(verification_results_list) else 'FAILED'}")
        print(f"  Verified {verified_count}/{len(verification_results_list)} hash(es)")
        
        integrity_results_list = integrity_results.get("integrity_results", [])
        integrity_ok = all(r.get("integrity_verified", False) for r in integrity_results_list)
        print(f"\nIntegrity Phase: {'PASSED' if integrity_ok else 'FAILED'}")
        print(f"  Integrity check: {'OK' if integrity_ok else 'FAILED'}")
        
        # Overall result
        all_passed = (
            len(uploaded_blobs) > 0 and
            len(processing_results) > 0 and
            verified_count == len(verification_results_list) and
            integrity_ok
        )
        
        test_results["success"] = all_passed
        
        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] All pipeline tests passed!")
        else:
            print("[PARTIAL] Some tests passed, review results above")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[ERROR] Test failed with exception:")
        print(f"  {type(e).__name__}: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        test_results["error"] = str(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

