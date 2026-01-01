"""
OmniTrust Storage Test Script
Tests connection to local Azurite storage and creates the raw media container.

This script:
1. Connects to local Azurite storage using development connection string
2. Creates a container called 'omnitrust-raw-media'
3. Uploads a small dummy text file to verify functionality

Usage:
    python src/services/test_storage.py
"""

import os
import sys
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError


def get_connection_string() -> str:
    """
    Get the Azure Storage connection string.
    
    For local development, uses the full Azurite connection string.
    For production, would read from environment variables or Azure Key Vault.
    
    Returns:
        Connection string for Azure Storage.
    """
    # Check environment variable first (for production/testing flexibility)
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not connection_string:
        # Use full development storage connection string for local Azurite
        # This is the expanded form of UseDevelopmentStorage=true
        connection_string = (
            "DefaultEndpointsProtocol=http;"
            "AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
            "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        )
    
    return connection_string


def create_container(client: BlobServiceClient, container_name: str) -> bool:
    """
    Create a blob container if it doesn't exist.
    
    Args:
        client: BlobServiceClient instance.
        container_name: Name of the container to create.
    
    Returns:
        True if container was created, False if it already existed.
    """
    try:
        container_client = client.create_container(container_name)
        print(f"[OK] Container '{container_name}' created successfully")
        return True
    except ResourceExistsError:
        print(f"[OK] Container '{container_name}' already exists")
        return False
    except HttpResponseError as e:
        print(f"[ERROR] Error creating container: {e}")
        raise


def upload_test_file(client: BlobServiceClient, container_name: str) -> str:
    """
    Upload a small dummy text file to the container.
    
    Args:
        client: BlobServiceClient instance.
        container_name: Name of the container.
    
    Returns:
        Name of the uploaded blob.
    """
    # Create dummy file content
    test_content = f"""OmniTrust Test File
Uploaded at: {datetime.now(timezone.utc).isoformat()}
Purpose: Storage connectivity test for raw media ingestion pipeline

This is a test file to verify Azure Blob Storage connectivity
and container creation for the OmniTrust media verification system.
"""
    
    # Generate a unique blob name
    blob_name = f"test/test_file_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        # Get container client
        container_client = client.get_container_client(container_name)
        
        # Upload the blob
        blob_client = container_client.upload_blob(
            name=blob_name,
            data=test_content.encode('utf-8'),
            overwrite=True
        )
        
        print(f"[OK] Test file uploaded successfully: {blob_name}")
        print(f"  Blob URL: {blob_client.url}")
        
        return blob_name
    except HttpResponseError as e:
        print(f"[ERROR] Error uploading file: {e}")
        raise


def list_blobs(client: BlobServiceClient, container_name: str):
    """
    List all blobs in the container.
    
    Args:
        client: BlobServiceClient instance.
        container_name: Name of the container.
    """
    try:
        container_client = client.get_container_client(container_name)
        blobs = container_client.list_blobs()
        
        blob_list = list(blobs)
        if blob_list:
            print(f"\n[OK] Found {len(blob_list)} blob(s) in container:")
            for blob in blob_list:
                print(f"  - {blob.name} ({blob.size} bytes, modified: {blob.last_modified})")
        else:
            print("\n[OK] Container is empty")
    except HttpResponseError as e:
        print(f"[ERROR] Error listing blobs: {e}")


def main():
    """Main test function."""
    print("=" * 60)
    print("OmniTrust Storage Test - Azurite Connection")
    print("=" * 60)
    
    # Container name as specified in project plan (for raw media ingestion)
    CONTAINER_NAME = "omnitrust-raw-media"
    
    try:
        # Get connection string
        connection_string = get_connection_string()
        print(f"\n1. Connecting to storage...")
        print(f"   Connection: {'Azurite (local)' if '127.0.0.1' in connection_string or 'devstoreaccount1' in connection_string else 'Azure Cloud'}")
        
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Test connection by getting account info
        account_info = blob_service_client.get_account_information()
        print(f"[OK] Connected successfully")
        print(f"   Account SKU: {account_info.get('sku_name', 'N/A')}")
        
        # Create container
        print(f"\n2. Creating container '{CONTAINER_NAME}'...")
        create_container(blob_service_client, CONTAINER_NAME)
        
        # Upload test file
        print(f"\n3. Uploading test file...")
        blob_name = upload_test_file(blob_service_client, CONTAINER_NAME)
        
        # List blobs to verify
        print(f"\n4. Verifying upload...")
        list_blobs(blob_service_client, CONTAINER_NAME)
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed successfully!")
        print("=" * 60)
        print(f"\nContainer '{CONTAINER_NAME}' is ready for media ingestion.")
        print("You can now use this container in your OmniTrust workflow.")
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Ensure Azurite is running on default ports (10000, 10001, 10002)")
        print("2. Check that azure-storage-blob package is installed")
        print("3. Verify connection string is correct")
        return 1


if __name__ == "__main__":
    sys.exit(main())

