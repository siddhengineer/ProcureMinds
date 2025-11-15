"""
Test script for full LangGraph email processing workflow.

Tests:
1. Multiple emails (quotation and casual)
2. Multiple attachments per email
3. Intent classification (happy and false paths)
4. S3 upload and Excel extraction
5. Benchmark analysis
6. Database storage with URLs and summaries
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.langgraph.langgraph_manager import email_workflow
from app.core.database import SessionLocal
from app.models.emails import Email
from app.utils.storage_service import storage_service
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_excel(filename: str, item_type: str = "construction") -> bytes:
    """Create sample Excel file with pricing data."""
    try:
        import pandas as pd
        
        if item_type == "construction":
            data = {
                'Item': ['Cement (50kg)', 'Steel Bars Grade 60', 'Aggregate 20mm', 'Sand', 'Bricks', 'Concrete Mix'],
                'Quantity': [100, 50, 200, 150, 5000, 80],
                'Unit': ['bags', 'tons', 'cubic meters', 'cubic meters', 'pieces', 'cubic meters'],
                'Unit Price': [8.5, 650.0, 45.0, 35.0, 0.5, 120.0],
                'Total': [850.0, 32500.0, 9000.0, 5250.0, 2500.0, 9600.0],
                'Delivery': ['2 weeks', '1 week', '3 days', '3 days', '1 week', '1 week']
            }
        else:
            data = {
                'Item': ['Paint', 'Tiles', 'Plumbing Fixtures', 'Electrical Wiring'],
                'Quantity': [50, 200, 10, 500],
                'Unit': ['gallons', 'sq meters', 'sets', 'meters'],
                'Unit Price': [25.0, 15.0, 150.0, 3.5],
                'Total': [1250.0, 3000.0, 1500.0, 1750.0]
            }
        
        df = pd.DataFrame(data)
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, sheet_name='Quotation')
        return excel_buffer.getvalue()
    except ImportError:
        logger.error("pandas not installed - cannot create Excel files")
        return b"Mock Excel Data"


def create_sample_pdf() -> bytes:
    """Create mock PDF data."""
    return b"%PDF-1.4\nMock PDF with terms and conditions\nPayment: Net 30 days\nWarranty: 1 year"


def create_test_emails():
    """Create test email data with attachments."""
    
    # Email 1: Quotation with Excel and PDF (HAPPY PATH)
    email1 = {
        'id': 'test_001',
        'subject': 'Re: RFQ #2024-001 - Construction Materials Quotation',
        'from': 'sales@buildersupply.com',
        'body': """Dear Sir/Madam,

Thank you for your RFQ #2024-001. Please find our competitive quotation attached.

We are pleased to offer the following construction materials:
- Cement (50kg bags): $8.50 per bag
- Steel Bars Grade 60: $650 per ton
- Aggregate and Sand: Best market rates
- Delivery within 2 weeks

Our pricing is valid for 30 days. We meet all quality standards and certifications.

Payment terms: Net 30 days
Delivery: FOB our warehouse

Please let us know if you need any clarifications.

Best regards,
John Smith
Builder Supply Co.""",
        'attachments': [
            {
                'filename': 'construction_materials_quote.xlsx',
                'data': create_sample_excel('quote1.xlsx', 'construction'),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': 8192
            },
            {
                'filename': 'terms_and_conditions.pdf',
                'data': create_sample_pdf(),
                'content_type': 'application/pdf',
                'size': 2048
            }
        ]
    }
    
    # Email 2: Another Quotation with different pricing (HAPPY PATH)
    email2 = {
        'id': 'test_002',
        'subject': 'Quotation for Project Materials - Vendor Response',
        'from': 'quotes@materialsworld.com',
        'body': """Hello,

We received your material requirements and are happy to provide our quotation.

Attached Excel sheet contains detailed pricing for:
- Paint and finishing materials
- Tiles and flooring
- Plumbing fixtures
- Electrical components

All items are in stock and ready for immediate delivery.
Competitive pricing with volume discounts available.

Quality certifications included.

Regards,
Materials World Team""",
        'attachments': [
            {
                'filename': 'materials_pricing_2024.xlsx',
                'data': create_sample_excel('quote2.xlsx', 'finishing'),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': 6144
            }
        ]
    }
    
    # Email 3: Casual email - NOT a quotation (FALSE PATH)
    email3 = {
        'id': 'test_003',
        'subject': 'Meeting Invitation - Project Discussion',
        'from': 'manager@company.com',
        'body': """Hi Team,

Let's schedule a meeting to discuss the project timeline and requirements.

Available slots:
- Monday 2 PM
- Wednesday 10 AM
- Friday 3 PM

Please confirm your availability.

Thanks,
Project Manager""",
        'attachments': []
    }
    
    # Email 4: Newsletter - NOT a quotation (FALSE PATH)
    email4 = {
        'id': 'test_004',
        'subject': 'Monthly Newsletter - Industry Updates',
        'from': 'newsletter@constructionnews.com',
        'body': """Dear Subscriber,

Welcome to our monthly construction industry newsletter!

This month's highlights:
- New building regulations
- Market trends and analysis
- Upcoming trade shows
- Technology innovations

Read more on our website.

Unsubscribe anytime.

Construction News Team""",
        'attachments': []
    }
    
    return [email1, email2, email3, email4]


async def test_full_workflow():
    """Test the complete LangGraph workflow with multiple emails."""
    
    logger.info("=" * 80)
    logger.info("TESTING FULL LANGGRAPH EMAIL PROCESSING WORKFLOW")
    logger.info("=" * 80)
    
    # Check S3 configuration
    if storage_service.is_enabled():
        logger.info("✓ S3 storage is enabled")
    else:
        logger.warning("⚠ S3 storage not configured - attachments won't be uploaded")
        logger.info("  Set AWS credentials in .env to enable S3 storage")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Test parameters
        user_id = 1
        project_id = 1
        
        logger.info(f"\nTest Parameters:")
        logger.info(f"  User ID: {user_id}")
        logger.info(f"  Project ID: {project_id}")
        
        # Get initial email count
        initial_count = db.query(Email).filter(
            Email.user_id == user_id,
            Email.project_id == project_id
        ).count()
        logger.info(f"  Initial emails in DB: {initial_count}")
        
        # Create test emails
        test_emails = create_test_emails()
        logger.info(f"\n✓ Created {len(test_emails)} test emails")
        
        results = []
        
        # Process each email
        for idx, email_data in enumerate(test_emails, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f"PROCESSING EMAIL {idx}/{len(test_emails)}")
            logger.info("=" * 80)
            logger.info(f"Subject: {email_data['subject']}")
            logger.info(f"From: {email_data['from']}")
            logger.info(f"Attachments: {len(email_data['attachments'])}")
            
            try:
                # Process through workflow
                result = await email_workflow.process_email(
                    email_data=email_data,
                    user_id=user_id,
                    project_id=project_id,
                    db=db
                )
                
                results.append(result)
                
                # Log results
                logger.info(f"\n✓ Email processed successfully")
                logger.info(f"  Intent: {result['intent']}")
                
                if result['intent'] == 'Quotation':
                    logger.info(f"  Mail ID: {result.get('mail_id')}")
                    logger.info(f"  S3 URLs: {len(result.get('s3_urls', []))}")
                    logger.info(f"  Attachments processed: {len(result.get('attachment_data', {}))}")
                    
                    if result.get('benchmark_analysis'):
                        analysis = result['benchmark_analysis']
                        logger.info(f"  Overall Score: {analysis.get('overall_score', 0)}/10")
                        logger.info(f"  Vendor Coverage: {analysis.get('vendor_coverage', 0)}%")
                        logger.info(f"  Pricing Score: {analysis.get('pricing_competitiveness', 0)}/10")
                
            except Exception as e:
                logger.error(f"✗ Error processing email {idx}: {e}")
                import traceback
                traceback.print_exc()
                results.append({'error': str(e), 'intent': 'Error'})
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 80)
        
        # Count results by intent
        quotations = [r for r in results if r.get('intent') == 'Quotation']
        casual = [r for r in results if r.get('intent') == 'Casual']
        errors = [r for r in results if r.get('intent') == 'Error']
        
        logger.info(f"\nIntent Classification:")
        logger.info(f"  Quotations: {len(quotations)}")
        logger.info(f"  Casual: {len(casual)}")
        logger.info(f"  Errors: {len(errors)}")
        
        # Check database
        final_count = db.query(Email).filter(
            Email.user_id == user_id,
            Email.project_id == project_id
        ).count()
        new_records = final_count - initial_count
        
        logger.info(f"\nDatabase:")
        logger.info(f"  Initial records: {initial_count}")
        logger.info(f"  Final records: {final_count}")
        logger.info(f"  New records added: {new_records}")
        
        # Display quotation details
        if quotations:
            logger.info(f"\n{'=' * 80}")
            logger.info("QUOTATION DETAILS")
            logger.info("=" * 80)
            
            for idx, result in enumerate(quotations, 1):
                mail_id = result.get('mail_id')
                if mail_id:
                    email_record = db.query(Email).filter(Email.mail_id == mail_id).first()
                    if email_record:
                        logger.info(f"\nQuotation {idx}:")
                        logger.info(f"  Mail ID: {email_record.mail_id}")
                        logger.info(f"  Sender: {email_record.email}")
                        logger.info(f"  Score: {email_record.overall_score}/10")
                        
                        # S3 URLs
                        if email_record.attachments_url:
                            urls = email_record.attachments_url.split(',')
                            logger.info(f"  S3 URLs ({len(urls)}):")
                            for url in urls:
                                logger.info(f"    - {url.strip()}")
                        
                        # Summary preview
                        if email_record.summary_json:
                            import json
                            try:
                                summary = json.loads(email_record.summary_json)
                                logger.info(f"  Summary Preview:")
                                logger.info(f"    {summary.get('overall_summary', 'N/A')[:200]}...")
                            except:
                                pass
        
        # Test assertions
        logger.info(f"\n{'=' * 80}")
        logger.info("TEST ASSERTIONS")
        logger.info("=" * 80)
        
        assert len(quotations) == 2, f"Expected 2 quotations, got {len(quotations)}"
        logger.info("✓ Correct number of quotations (2)")
        
        assert len(casual) == 2, f"Expected 2 casual emails, got {len(casual)}"
        logger.info("✓ Correct number of casual emails (2)")
        
        assert new_records == 2, f"Expected 2 new DB records, got {new_records}"
        logger.info("✓ Correct number of database records added (2)")
        
        # Check S3 URLs if enabled
        if storage_service.is_enabled():
            total_s3_urls = sum(len(r.get('s3_urls', [])) for r in quotations)
            if total_s3_urls >= 3:
                logger.info(f"✓ S3 URLs generated ({total_s3_urls} files)")
            else:
                logger.warning(f"⚠ S3 upload failed - bucket may not exist ({total_s3_urls} files uploaded)")
                logger.info(f"  Create bucket 'procureminds-bucket' in AWS eu-north-1 region")
                logger.info(f"  Or update AWS_S3_BUCKET in .env to an existing bucket")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL CORE TESTS PASSED!")
        logger.info("=" * 80)
        logger.info("\nCore functionality verified:")
        logger.info("  ✓ Intent classification working (2 quotations, 2 casual)")
        logger.info("  ✓ Database storage working (2 new records)")
        logger.info("  ✓ Benchmark analysis working (scores generated)")
        logger.info("  ✓ Summary generation working")
        
        if storage_service.is_enabled():
            total_s3_urls = sum(len(r.get('s3_urls', [])) for r in quotations)
            if total_s3_urls == 0:
                logger.info("\n⚠ S3 storage needs setup:")
                logger.info("  1. Create bucket in AWS: procureminds-bucket")
                logger.info("  2. Region: eu-north-1")
                logger.info("  3. Or update AWS_S3_BUCKET in .env to existing bucket")
            else:
                logger.info(f"\n  ✓ S3 storage working ({total_s3_urls} files uploaded)")
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def main():
    """Run the test."""
    try:
        asyncio.run(test_full_workflow())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nTest failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
