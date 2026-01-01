"""
OmniTrust Ledger Service (Sprint 1)
Azure Confidential Ledger integration for immutable hash anchoring.

Implements "Birth Certificate" functionality by anchoring SHA-256 hashes
of raw video and metadata to an immutable Intel SGX enclave.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, Union, BinaryIO
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.confidentialledger import ConfidentialLedgerClient
from azure.confidentialledger.certificate import ConfidentialLedgerCertificateClient
from azure.core.exceptions import HttpResponseError, ServiceRequestError


class LedgerService:
    """
    Service for anchoring media hashes to Azure Confidential Ledger.
    
    Creates permanent, mathematically unchangeable "Truth Receipts" by
    storing SHA-256 hashes in an immutable ledger backed by Intel SGX enclaves.
    """
    
    def __init__(
        self,
        ledger_name: Optional[str] = None,
        ledger_url: Optional[str] = None,
        identity_url: str = "https://identity.confidential-ledger.core.azure.com"
    ):
        """
        Initialize the Ledger Service.
        
        Args:
            ledger_name: Name of the Azure Confidential Ledger instance.
                        If not provided, reads from LEDGER_NAME env var.
            ledger_url: Full URL of the ledger endpoint.
                       If not provided, constructs from ledger_name.
            identity_url: Identity service URL for certificate retrieval.
        """
        self.ledger_name = ledger_name or os.getenv("LEDGER_NAME")
        if not self.ledger_name and not ledger_url:
            raise ValueError("ledger_name or LEDGER_NAME env var is required")
        
        self.ledger_url = ledger_url or f"https://{self.ledger_name}.confidential-ledger.azure.com"
        self.identity_url = identity_url
        self.credential = DefaultAzureCredential()
        self._ledger_client: Optional[ConfidentialLedgerClient] = None
    
    def _get_ledger_client(self) -> ConfidentialLedgerClient:
        """
        Get or create the Confidential Ledger client with certificate handling.
        
        Returns:
            Initialized ConfidentialLedgerClient instance.
        """
        if self._ledger_client is not None:
            return self._ledger_client
        
        # Retrieve the ledger's TLS certificate
        cert_client = ConfidentialLedgerCertificateClient(self.identity_url)
        network_identity = cert_client.get_ledger_identity(ledger_id=self.ledger_name)
        ledger_tls_cert = network_identity['ledgerTlsCertificate']
        
        # Save certificate to temporary file (or use in-memory for production)
        # For production, consider caching or using certificate store
        cert_file_path = os.path.join(os.path.dirname(__file__), ".ledger_cert.pem")
        with open(cert_file_path, "w") as cert_file:
            cert_file.write(ledger_tls_cert)
        
        # Initialize the Confidential Ledger client
        self._ledger_client = ConfidentialLedgerClient(
            endpoint=self.ledger_url,
            credential=self.credential,
            ledger_certificate_path=cert_file_path
        )
        
        return self._ledger_client
    
    @staticmethod
    def compute_sha256(file_input: Union[str, Path, bytes, BinaryIO]) -> str:
        """
        Compute SHA-256 hash of a video file or bytes.
        
        Supports multiple input types:
        - File path (str or Path)
        - Raw bytes
        - File-like object (BinaryIO)
        
        Args:
            file_input: Video file path, bytes, or file-like object.
        
        Returns:
            Hexadecimal SHA-256 hash string.
        """
        sha256_hash = hashlib.sha256()
        
        if isinstance(file_input, (str, Path)):
            # File path
            with open(file_input, "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
        elif isinstance(file_input, bytes):
            # Raw bytes
            sha256_hash.update(file_input)
        else:
            # File-like object (BinaryIO)
            # Read from current position, don't seek to start
            for byte_block in iter(lambda: file_input.read(8192), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def anchor_hash(
        self,
        video_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        c2pa_manifest: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Anchor a video hash to the Confidential Ledger (Sprint 1).
        
        Creates an immutable ledger entry containing:
        - SHA-256 hash of the video
        - Optional C2PA manifest (GPS, Hardware ID, Timestamp)
        - Additional metadata
        
        Args:
            video_hash: SHA-256 hash of the video file.
            metadata: Optional additional metadata to store.
            c2pa_manifest: Optional C2PA manifest data (GPS, Hardware ID, Timestamp).
        
        Returns:
            Dictionary containing:
            - transaction_id: Ledger transaction ID
            - entry_id: Ledger entry ID
            - timestamp: UTC timestamp of the anchor
            - hash: The anchored hash (for verification)
        """
        ledger_client = self._get_ledger_client()
        
        # Prepare ledger entry with hash and metadata
        entry_data = {
            "hash": video_hash,
            "type": "media_verification",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Add C2PA manifest if provided (Sprint 1: C2PA Handshake)
        if c2pa_manifest:
            entry_data["c2pa_manifest"] = c2pa_manifest
            entry_data["source"] = "c2pa_compliant"
        
        # Add additional metadata
        if metadata:
            entry_data["metadata"] = metadata
        
        # Create ledger entry
        try:
            append_result = ledger_client.create_ledger_entry(entry=entry_data)
            
            transaction_id = append_result['transactionId']
            entry_id = append_result.get('entryId', transaction_id)
            
            return {
                "transaction_id": transaction_id,
                "entry_id": entry_id,
                "timestamp": entry_data["timestamp"],
                "hash": video_hash,
                "status": "anchored"
            }
        except (HttpResponseError, ServiceRequestError) as e:
            raise RuntimeError(f"Failed to anchor hash to ledger: {str(e)}") from e
    
    def anchor_video_file(
        self,
        video_file: Union[str, Path, bytes, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None,
        c2pa_manifest: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compute hash and anchor a video file to the ledger in one operation.
        
        This is the primary method for Sprint 1 workflow.
        
        Args:
            video_file: Video file path, bytes, or file-like object.
            metadata: Optional additional metadata.
            c2pa_manifest: Optional C2PA manifest data.
        
        Returns:
            Dictionary containing transaction_id, entry_id, hash, and status.
        """
        # Compute SHA-256 hash
        video_hash = self.compute_sha256(video_file)
        
        # Anchor to ledger
        return self.anchor_hash(
            video_hash=video_hash,
            metadata=metadata,
            c2pa_manifest=c2pa_manifest
        )
    
    def verify_hash(
        self,
        video_hash: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a video hash exists in the ledger (zero-tampering proof).
        
        Used for integrity checks by comparing live hash to ledger entries.
        
        Args:
            video_hash: SHA-256 hash to verify.
            transaction_id: Optional transaction ID to check specific entry.
        
        Returns:
            Dictionary containing:
            - verified: Boolean indicating if hash was found
            - transaction_id: Transaction ID if found
            - entry_id: Entry ID if found
            - timestamp: Timestamp of the ledger entry if found
        """
        ledger_client = self._get_ledger_client()
        
        try:
            if transaction_id:
                # Get specific entry by transaction ID
                entry = ledger_client.get_ledger_entry(transaction_id=transaction_id)
                entry_data = entry.get('entry', {})
                
                if isinstance(entry_data, str):
                    entry_data = json.loads(entry_data)
                
                stored_hash = entry_data.get('hash')
                
                if stored_hash == video_hash:
                    return {
                        "verified": True,
                        "transaction_id": transaction_id,
                        "entry_id": entry.get('entryId'),
                        "timestamp": entry_data.get('timestamp'),
                        "status": "integrity_confirmed"
                    }
            else:
                # Search for hash in recent entries (limited to recent transactions)
                # Note: Full ledger scan requires pagination and may be expensive
                # For production, consider maintaining an index or using query patterns
                current_state = ledger_client.get_current_ledger_entry()
                # This is a simplified check - production may need more sophisticated search
                
            return {
                "verified": False,
                "status": "hash_not_found"
            }
        except (HttpResponseError, ServiceRequestError) as e:
            raise RuntimeError(f"Failed to verify hash in ledger: {str(e)}") from e
    
    def extract_c2pa_metadata(
        self,
        video_file: Union[str, Path, bytes]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract C2PA manifest metadata from video file.
        
        This is a placeholder for C2PA manifest extraction.
        In production, use a C2PA library (e.g., c2patool) to extract:
        - GPS coordinates
        - Hardware ID (camera serial number)
        - Timestamp
        - Other C2PA assertions
        
        Args:
            video_file: Video file path or bytes.
        
        Returns:
            Dictionary with C2PA manifest data, or None if not C2PA-compliant.
        """
        # TODO: Integrate with C2PA library (e.g., c2patool or c2pa-python)
        # For Sprint 1, this is a placeholder structure
        # Actual implementation would use:
        # from c2pa import read_file
        # manifest = read_file(video_file)
        # return {
        #     "gps": manifest.get("gps"),
        #     "hardware_id": manifest.get("hardware_id"),
        #     "timestamp": manifest.get("timestamp"),
        #     "camera_make": manifest.get("camera_make"),
        #     "camera_model": manifest.get("camera_model")
        # }
        
        # Placeholder: Return None to indicate no C2PA manifest found
        # This allows the workflow to proceed with standard verification
        return None


# Convenience functions for direct usage
def anchor_video_to_ledger(
    video_file: Union[str, Path, bytes, BinaryIO],
    ledger_name: Optional[str] = None,
    c2pa_manifest: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to anchor a video file to the ledger.
    
    Args:
        video_file: Video file path, bytes, or file-like object.
        ledger_name: Name of the Azure Confidential Ledger instance.
        c2pa_manifest: Optional C2PA manifest data.
        metadata: Optional additional metadata.
    
    Returns:
        Dictionary with transaction_id, entry_id, hash, and status.
    """
    service = LedgerService(ledger_name=ledger_name)
    return service.anchor_video_file(
        video_file=video_file,
        metadata=metadata,
        c2pa_manifest=c2pa_manifest
    )


def verify_video_hash(
    video_hash: str,
    transaction_id: Optional[str] = None,
    ledger_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to verify a video hash in the ledger.
    
    Args:
        video_hash: SHA-256 hash to verify.
        transaction_id: Optional transaction ID.
        ledger_name: Name of the Azure Confidential Ledger instance.
    
    Returns:
        Dictionary with verification result.
    """
    service = LedgerService(ledger_name=ledger_name)
    return service.verify_hash(video_hash=video_hash, transaction_id=transaction_id)

