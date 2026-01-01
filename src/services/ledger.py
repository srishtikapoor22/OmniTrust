"""
OmniTrust Ledger Service (Sprint 1 - Local Mock)
Azure Blob Storage monitoring and hash computation service.

Monitors the 'omnitrust-raw-media' container for new files,
computes SHA-256 hashes, and stores them in a local mock ledger
file to simulate Azure Confidential Ledger functionality.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError


def get_connection_string() -> str:
    """
    Get the Azure Storage connection string.
    
    For local development, uses the full Azurite connection string.
    For production, would read from environment variables or Azure Key Vault.
    
    Returns:
        Connection string for Azure Storage.
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not connection_string:
        # Use full development storage connection string for local Azurite
        connection_string = (
            "DefaultEndpointsProtocol=http;"
            "AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
            "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        )
    
    return connection_string


class LedgerMonitorService:
    """
    Service for monitoring blob storage and anchoring media hashes.
    
    Monitors the 'omnitrust-raw-media' container for new files,
    computes SHA-256 hashes, and stores them in a local mock ledger file.
    This simulates the Azure Confidential Ledger "Birth Certificate" functionality.
    """
    
    def __init__(
        self,
        container_name: str = "omnitrust-raw-media",
        connection_string: Optional[str] = None,
        ledger_file: str = "mock_ledger.json"
    ):
        """
        Initialize the Ledger Monitor Service.
        
        Args:
            container_name: Name of the blob container to monitor.
            connection_string: Azure Storage connection string.
                            If not provided, uses get_connection_string().
            ledger_file: Path to the local JSON file for storing ledger entries.
        """
        self.container_name = container_name
        self.connection_string = connection_string or get_connection_string()
        self.ledger_file = Path(ledger_file)
        
        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        self.container_client = self.blob_service_client.get_container_client(
            container_name
        )
        
        # Load existing ledger to track processed blobs
        self._ledger_data = self._load_ledger()
    
    @staticmethod
    def compute_sha256(file_input: bytes) -> str:
        """
        Compute SHA-256 hash of file bytes.
        
        Args:
            file_input: File content as bytes.
        
        Returns:
            Hexadecimal SHA-256 hash string.
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_input)
        return sha256_hash.hexdigest()
    
    def _load_ledger(self) -> Dict[str, Any]:
        """
        Load the mock ledger JSON file.
        
        Returns:
            Dictionary containing ledger data with structure:
            {
                "entries": [
                    {
                        "transaction_id": str,
                        "blob_name": str,
                        "hash": str,
                        "timestamp": str,
                        "size": int,
                        "last_modified": str
                    }
                ],
                "processed_blobs": [str]  # List of blob names already processed
            }
        """
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load ledger file: {e}. Creating new ledger.")
        
        # Return default structure
        return {
            "entries": [],
            "processed_blobs": []
        }
    
    def _save_ledger(self):
        """Save the ledger data to the JSON file."""
        try:
            # Ensure directory exists
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.ledger_file, 'w', encoding='utf-8') as f:
                json.dump(self._ledger_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise RuntimeError(f"Failed to save ledger file: {e}") from e
    
    def _get_processed_blobs(self) -> Set[str]:
        """Get set of blob names that have already been processed."""
        return set(self._ledger_data.get("processed_blobs", []))
    
    def _mark_blob_processed(self, blob_name: str):
        """Mark a blob as processed in the ledger."""
        processed = self._get_processed_blobs()
        processed.add(blob_name)
        self._ledger_data["processed_blobs"] = list(processed)
    
    def list_new_blobs(self) -> List[Dict[str, Any]]:
        """
        List blobs in the container that haven't been processed yet.
        
        Returns:
            List of blob metadata dictionaries for new blobs.
        """
        try:
            processed_blobs = self._get_processed_blobs()
            new_blobs = []
            
            # List all blobs in the container
            blobs = self.container_client.list_blobs()
            
            for blob in blobs:
                # Skip if already processed
                if blob.name not in processed_blobs:
                    new_blobs.append({
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                        "content_type": blob.content_settings.content_type if blob.content_settings else None
                    })
            
            return new_blobs
        except HttpResponseError as e:
            raise RuntimeError(f"Failed to list blobs: {e}") from e
    
    def process_blob(self, blob_name: str) -> Dict[str, Any]:
        """
        Process a single blob: download, compute hash, and store in ledger.
        
        Args:
            blob_name: Name of the blob to process.
        
        Returns:
            Dictionary containing transaction_id, hash, and metadata.
        """
        try:
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Get blob properties
            blob_props = blob_client.get_blob_properties()
            
            # Download blob content
            blob_data = blob_client.download_blob().readall()
            
            # Compute SHA-256 hash
            video_hash = self.compute_sha256(blob_data)
            
            # Generate transaction ID (simulating ledger transaction)
            transaction_id = f"txn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Create ledger entry
            entry = {
                "transaction_id": transaction_id,
                "blob_name": blob_name,
                "hash": video_hash,
                "timestamp": timestamp,
                "size": blob_props.size,
                "last_modified": blob_props.last_modified.isoformat() if blob_props.last_modified else None,
                "content_type": blob_props.content_settings.content_type if blob_props.content_settings else None,
                "etag": blob_props.etag,
                "status": "anchored"
            }
            
            # Add to ledger
            self._ledger_data["entries"].append(entry)
            self._mark_blob_processed(blob_name)
            self._save_ledger()
            
            return {
                "transaction_id": transaction_id,
                "entry_id": transaction_id,
                "blob_name": blob_name,
                "hash": video_hash,
                "timestamp": timestamp,
                "status": "anchored"
            }
            
        except (HttpResponseError, ResourceNotFoundError) as e:
            raise RuntimeError(f"Failed to process blob '{blob_name}': {e}") from e
    
    def monitor_and_process(self) -> List[Dict[str, Any]]:
        """
        Monitor the container for new blobs and process them.
        
        This is the main method for continuous monitoring. It finds all
        unprocessed blobs, computes their hashes, and stores them in the ledger.
        
        Returns:
            List of processing results for each new blob.
        """
        results = []
        
        # Find new blobs
        new_blobs = self.list_new_blobs()
        
        if not new_blobs:
            return results
        
        print(f"Found {len(new_blobs)} new blob(s) to process")
        
        # Process each new blob
        for blob_info in new_blobs:
            blob_name = blob_info["name"]
            try:
                print(f"Processing blob: {blob_name}")
                result = self.process_blob(blob_name)
                results.append(result)
                print(f"  [OK] Hash computed: {result['hash'][:16]}... (txn: {result['transaction_id']})")
            except Exception as e:
                print(f"  [ERROR] Failed to process {blob_name}: {e}")
                results.append({
                    "blob_name": blob_name,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def get_entry_by_hash(self, video_hash: str) -> Optional[Dict[str, Any]]:
        """
        Find a ledger entry by hash (for verification).
        
        Args:
            video_hash: SHA-256 hash to search for.
        
        Returns:
            Ledger entry dictionary if found, None otherwise.
        """
        for entry in self._ledger_data.get("entries", []):
            if entry.get("hash") == video_hash:
                return entry
        return None
    
    def get_entry_by_blob_name(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a ledger entry by blob name.
        
        Args:
            blob_name: Name of the blob to search for.
        
        Returns:
            Ledger entry dictionary if found, None otherwise.
        """
        for entry in self._ledger_data.get("entries", []):
            if entry.get("blob_name") == blob_name:
                return entry
        return None
    
    def verify_hash(self, video_hash: str) -> Dict[str, Any]:
        """
        Verify if a hash exists in the ledger (zero-tampering proof).
        
        Args:
            video_hash: SHA-256 hash to verify.
        
        Returns:
            Dictionary with verification result.
        """
        entry = self.get_entry_by_hash(video_hash)
        
        if entry:
            return {
                "verified": True,
                "transaction_id": entry.get("transaction_id"),
                "entry_id": entry.get("transaction_id"),
                "blob_name": entry.get("blob_name"),
                "timestamp": entry.get("timestamp"),
                "status": "integrity_confirmed"
            }
        else:
            return {
                "verified": False,
                "status": "hash_not_found"
            }
    
    def get_ledger_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the ledger.
        
        Returns:
            Dictionary with ledger statistics.
        """
        entries = self._ledger_data.get("entries", [])
        processed = len(self._get_processed_blobs())
        
        return {
            "total_entries": len(entries),
            "processed_blobs": processed,
            "ledger_file": str(self.ledger_file),
            "container_name": self.container_name,
            "latest_entry": entries[-1] if entries else None
        }


# Convenience function for one-time monitoring
def monitor_and_process_blobs(
    container_name: str = "omnitrust-raw-media",
    ledger_file: str = "mock_ledger.json"
) -> List[Dict[str, Any]]:
    """
    Convenience function to monitor and process new blobs.
    
    Args:
        container_name: Name of the blob container to monitor.
        ledger_file: Path to the local JSON file for storing ledger entries.
    
    Returns:
        List of processing results.
    """
    service = LedgerMonitorService(
        container_name=container_name,
        ledger_file=ledger_file
    )
    return service.monitor_and_process()


if __name__ == "__main__":
    """
    Run the monitor service as a standalone script.
    """
    import sys
    
    print("=" * 60)
    print("OmniTrust Ledger Monitor Service")
    print("=" * 60)
    
    try:
        service = LedgerMonitorService()
        
        # Show current stats
        stats = service.get_ledger_stats()
        print(f"\nLedger Stats:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Processed blobs: {stats['processed_blobs']}")
        print(f"  Ledger file: {stats['ledger_file']}")
        
        # Monitor and process new blobs
        print(f"\nMonitoring container '{service.container_name}'...")
        results = service.monitor_and_process()
        
        if results:
            print(f"\n[SUCCESS] Processed {len(results)} blob(s)")
        else:
            print("\n[INFO] No new blobs to process")
        
        # Show updated stats
        stats = service.get_ledger_stats()
        print(f"\nUpdated Stats:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Processed blobs: {stats['processed_blobs']}")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)
