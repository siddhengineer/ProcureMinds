"""
Script to create the S3 bucket for ProcureMinds.
Run this once to set up your S3 storage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_s3_bucket():
    """Create S3 bucket if it doesn't exist."""
    
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        logger.error("AWS credentials not configured in .env")
        return False
    
    bucket_name = settings.aws_s3_bucket
    region = settings.aws_s3_region
    
    logger.info(f"Setting up S3 bucket: {bucket_name}")
    logger.info(f"Region: {region}")
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=region
        )
        
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"✓ Bucket '{bucket_name}' already exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Bucket doesn't exist, creating...")
            else:
                logger.error(f"Error checking bucket: {e}")
                return False
        
        # Create bucket
        if region == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        logger.info(f"✓ Bucket '{bucket_name}' created successfully")
        
        # Enable versioning (optional but recommended)
        try:
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            logger.info("✓ Versioning enabled")
        except Exception as e:
            logger.warning(f"Could not enable versioning: {e}")
        
        # Set bucket encryption (optional but recommended)
        try:
            s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            logger.info("✓ Encryption enabled")
        except Exception as e:
            logger.warning(f"Could not enable encryption: {e}")
        
        # Set lifecycle policy to delete old files (optional)
        try:
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'Id': 'DeleteOldAttachments',
                            'Status': 'Enabled',
                            'Prefix': 'attachments/',
                            'Expiration': {
                                'Days': 365  # Delete files older than 1 year
                            }
                        }
                    ]
                }
            )
            logger.info("✓ Lifecycle policy set (delete after 365 days)")
        except Exception as e:
            logger.warning(f"Could not set lifecycle policy: {e}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ S3 BUCKET SETUP COMPLETE")
        logger.info("=" * 80)
        logger.info(f"\nBucket URL: https://{bucket_name}.s3.{region}.amazonaws.com")
        logger.info(f"\nYou can now run: python examples/test_storage_service.py")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            logger.info(f"✓ Bucket '{bucket_name}' already exists and is owned by you")
            return True
        elif error_code == 'BucketAlreadyExists':
            logger.error(f"✗ Bucket name '{bucket_name}' is already taken by another AWS account")
            logger.info(f"  Choose a different bucket name in .env: AWS_S3_BUCKET=your-unique-name")
            return False
        else:
            logger.error(f"✗ Error creating bucket: {e}")
            return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bucket_access():
    """Test if we can write to the bucket."""
    
    bucket_name = settings.aws_s3_bucket
    region = settings.aws_s3_region
    
    logger.info("\nTesting bucket access...")
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=region
        )
        
        # Try to upload a test file
        test_key = 'test/test_file.txt'
        test_data = b'This is a test file'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_data
        )
        
        logger.info(f"✓ Successfully uploaded test file")
        
        # Try to download it
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_data = response['Body'].read()
        
        if downloaded_data == test_data:
            logger.info(f"✓ Successfully downloaded test file")
        
        # Delete test file
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        logger.info(f"✓ Successfully deleted test file")
        
        logger.info("\n✓ Bucket is fully functional!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Bucket access test failed: {e}")
        return False


def main():
    """Main setup function."""
    
    logger.info("=" * 80)
    logger.info("S3 BUCKET SETUP FOR PROCUREMINDS")
    logger.info("=" * 80)
    
    # Create bucket
    if create_s3_bucket():
        # Test access
        test_bucket_access()
    else:
        logger.error("\nSetup failed. Please check:")
        logger.error("  1. AWS credentials are correct in .env")
        logger.error("  2. IAM user has S3 permissions")
        logger.error("  3. Bucket name is unique")
        sys.exit(1)


if __name__ == "__main__":
    main()
