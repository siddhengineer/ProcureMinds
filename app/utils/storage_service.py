import boto3
import logging
import os
import io
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime
from pathlib import Path
import pandas as pd
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for managing file storage in AWS S3 and extracting data from files."""
    
    def __init__(self):
        """Initialize S3 client with credentials from settings."""
        self.s3_client = None
        self.bucket_name = settings.aws_s3_bucket
        self.region = settings.aws_s3_region
        self.base_url = settings.aws_s3_base_url
        
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=self.region
                )
                logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
        else:
            logger.warning("AWS credentials not configured, S3 storage disabled")
    
    def is_enabled(self) -> bool:
        """Check if S3 storage is properly configured."""
        return self.s3_client is not None and self.bucket_name is not None
    
    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        mail_id: int,
        user_id: int,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Upload a file to S3 bucket.
        
        Args:
            file_data: Binary file data
            filename: Original filename
            mail_id: Email ID for organizing files
            user_id: User ID for organizing files
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the file
            
        Returns:
            S3 URL of the uploaded file, or None if upload failed
        """
        if not self.is_enabled():
            logger.error("S3 storage is not enabled")
            return None
        
        try:
            # Generate S3 key with organized structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(filename).suffix
            safe_filename = Path(filename).stem.replace(" ", "_")
            
            s3_key = f"attachments/user_{user_id}/mail_{mail_id}/{timestamp}_{safe_filename}{file_extension}"
            
            # Prepare metadata
            upload_metadata = {
                "original_filename": filename,
                "mail_id": str(mail_id),
                "user_id": str(user_id),
                "upload_timestamp": timestamp
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata=upload_metadata
            )
            
            # Generate URL
            file_url = self._generate_url(s3_key)
            logger.info(f"Successfully uploaded file to S3: {file_url}")
            
            return file_url
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None
    
    def upload_attachment(
        self,
        attachment: Dict[str, Any],
        mail_id: int,
        user_id: int
    ) -> Optional[str]:
        """
        Upload an email attachment to S3.
        
        Args:
            attachment: Attachment dictionary with 'data', 'filename', 'content_type'
            mail_id: Email ID
            user_id: User ID
            
        Returns:
            S3 URL of the uploaded file
        """
        return self.upload_file(
            file_data=attachment.get("data"),
            filename=attachment.get("filename", "unknown"),
            mail_id=mail_id,
            user_id=user_id,
            content_type=attachment.get("content_type", "application/octet-stream"),
            metadata={
                "size": str(attachment.get("size", 0))
            }
        )
    
    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File data as bytes, or None if download failed
        """
        if not self.is_enabled():
            logger.error("S3 storage is not enabled")
            return None
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            file_data = response['Body'].read()
            logger.info(f"Successfully downloaded file from S3: {s3_key}")
            return file_data
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading file from S3: {e}")
            return None
    
    def download_file_by_url(self, file_url: str) -> Optional[bytes]:
        """
        Download a file from S3 using its URL.
        
        Args:
            file_url: Full S3 URL
            
        Returns:
            File data as bytes
        """
        # Extract S3 key from URL
        s3_key = self._extract_key_from_url(file_url)
        if not s3_key:
            logger.error(f"Could not extract S3 key from URL: {file_url}")
            return None
        
        return self.download_file(s3_key)
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if deletion was successful
        """
        if not self.is_enabled():
            logger.error("S3 storage is not enabled")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Successfully deleted file from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 deletion failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def extract_excel_data(self, file_data: bytes, filename: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from Excel file (xlsx, xls).
        
        Args:
            file_data: Binary Excel file data
            filename: Filename to determine Excel format
            
        Returns:
            Dictionary containing:
            - sheets: List of sheet names
            - data: Dictionary mapping sheet names to data summaries
            - row_count: Total rows across all sheets
            - column_info: Column information per sheet
        """
        try:
            # Read Excel file
            excel_file = io.BytesIO(file_data)
            
            # Determine engine based on file extension
            engine = 'openpyxl' if filename.endswith('.xlsx') else 'xlrd'
            
            # Read all sheets
            excel_data = pd.read_excel(excel_file, sheet_name=None, engine=engine)
            
            result = {
                "sheets": list(excel_data.keys()),
                "data": {},
                "row_count": 0,
                "column_info": {}
            }
            
            for sheet_name, df in excel_data.items():
                # Get basic info
                row_count = len(df)
                result["row_count"] += row_count
                
                # Get column information
                columns = df.columns.tolist()
                column_types = df.dtypes.astype(str).to_dict()
                
                result["column_info"][sheet_name] = {
                    "columns": columns,
                    "column_types": column_types,
                    "row_count": row_count
                }
                
                # Extract sample data (first 5 rows)
                sample_data = df.head(5).to_dict(orient='records')
                
                # Generate summary
                result["data"][sheet_name] = {
                    "sample_rows": sample_data,
                    "summary": self._generate_dataframe_summary(df)
                }
            
            logger.info(f"Successfully extracted data from Excel file: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting Excel data from {filename}: {e}")
            return None
    
    def extract_excel_from_s3(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Download and extract data from an Excel file stored in S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Extracted Excel data dictionary
        """
        file_data = self.download_file(s3_key)
        if not file_data:
            return None
        
        filename = Path(s3_key).name
        return self.extract_excel_data(file_data, filename)
    
    def _generate_dataframe_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a text summary of DataFrame contents."""
        summary = {
            "shape": f"{df.shape[0]} rows × {df.shape[1]} columns",
            "columns": df.columns.tolist(),
            "numeric_summary": {},
            "text_preview": {}
        }
        
        # Numeric columns summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            summary["numeric_summary"][col] = {
                "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None
            }
        
        # Text columns preview
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols[:5]:  # Limit to first 5 text columns
            unique_values = df[col].dropna().unique()[:5].tolist()
            summary["text_preview"][col] = unique_values
        
        return summary
    
    def _generate_url(self, s3_key: str) -> str:
        """Generate public URL for S3 object."""
        if self.base_url:
            return f"{self.base_url}/{s3_key}"
        else:
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    def _extract_key_from_url(self, file_url: str) -> Optional[str]:
        """Extract S3 key from full URL."""
        try:
            # Handle different URL formats
            if self.base_url and file_url.startswith(self.base_url):
                return file_url.replace(f"{self.base_url}/", "")
            elif f"{self.bucket_name}.s3" in file_url:
                parts = file_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")
                if len(parts) > 1:
                    return parts[1]
            return None
        except Exception as e:
            logger.error(f"Error extracting S3 key from URL: {e}")
            return None
    
    def get_file_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file in S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dictionary with file metadata
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "metadata": response.get("Metadata", {})
            }
            
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None


# Global instance
storage_service = S3StorageService()
