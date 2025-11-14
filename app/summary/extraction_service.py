import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from openai import OpenAI
import json

from app.summary.benchmark_queries import get_project_benchmarks_json
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client with OpenRouter
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


class BenchmarkExtractionService:
    """Service to extract benchmarks and analyze vendor emails against them."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_project_benchmarks(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Query all benchmark materials for a given project with category details.
        
        Args:
            project_id: The project ID to filter benchmarks
            
        Returns:
            List of benchmark dictionaries with category information
        """
        try:
            benchmarks = get_project_benchmarks_json(project_id, self.db)
            logger.info(f"Retrieved {len(benchmarks)} benchmarks for project {project_id}")
            return benchmarks
            
        except Exception as e:
            logger.error(f"Error retrieving benchmarks for project {project_id}: {e}")
            return []
    
    def analyze_vendor_email(
        self,
        project_id: int,
        email_subject: str,
        email_body: str,
        sender_email: str = "",
        attachments_info: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze vendor email and attachments against project benchmarks.
        
        Args:
            project_id: Project ID to get benchmarks for
            email_subject: Email subject line
            email_body: Email body text
            sender_email: Sender email address
            attachments_info: List of attachment metadata (filename, content summary, etc.)
            
        Returns:
            Dictionary containing:
            - vendor_email: Sender email address
            - overall_summary: Summary of how the email matches benchmarks
            - overall_score: Overall vendor score (0-10)
            - benchmark_scores: List of scores for each benchmark
            - vendor_coverage: Percentage of benchmarks covered
            - response_speed_score: Score for response speed
            - quality_match_score: Score for quality standard matching
            - pricing_competitiveness: Score for pricing (0-10)
            - professionalism_score: Score for email professionalism (0-10)
        """
        benchmarks = self.get_project_benchmarks(project_id)
        
        if not benchmarks:
            logger.warning(f"No benchmarks found for project {project_id}")
            return {
                "vendor_email": sender_email,
                "overall_summary": "No benchmarks available for comparison",
                "overall_score": 0,
                "benchmark_scores": [],
                "vendor_coverage": 0,
                "response_speed_score": 0,
                "quality_match_score": 0,
                "pricing_competitiveness": 0,
                "professionalism_score": 0
            }
        
        # Prepare context for AI analysis
        analysis_result = self._analyze_with_ai(
            benchmarks=benchmarks,
            email_subject=email_subject,
            email_body=email_body,
            attachments_info=attachments_info or []
        )
        
        # Add vendor email to result
        analysis_result["vendor_email"] = sender_email
        
        return analysis_result

    
    def _analyze_with_ai(
        self,
        benchmarks: List[Dict[str, Any]],
        email_subject: str,
        email_body: str,
        attachments_info: List[Dict]
    ) -> Dict[str, Any]:
        """
        Use AI to analyze vendor email against benchmarks.
        
        Args:
            benchmarks: List of benchmark dictionaries
            email_subject: Email subject
            email_body: Email body text
            attachments_info: Attachment information
            
        Returns:
            Analysis results with scores
        """
        try:
            # Prepare benchmark summary for AI
            benchmark_summary = self._format_benchmarks_for_ai(benchmarks)
            
            # Prepare enhanced attachments summary with Excel data
            attachments_summary_parts = []
            for att in attachments_info:
                filename = att.get('filename', 'Unknown')
                content_type = att.get('content_type', 'Unknown type')
                
                att_line = f"- {filename} ({content_type})"
                
                # Add Excel data summary if available
                if att.get('excel_summary'):
                    excel = att['excel_summary']
                    att_line += f"\n  Excel Data: {excel.get('total_rows', 0)} rows across {len(excel.get('sheets', []))} sheets"
                    
                    # Add column information
                    for sheet_name, sheet_info in excel.get('columns', {}).items():
                        columns = sheet_info.get('columns', [])
                        if columns:
                            att_line += f"\n  Sheet '{sheet_name}': {', '.join(columns[:5])}"
                            if len(columns) > 5:
                                att_line += f" ... ({len(columns)} total columns)"
                    
                    # Add data preview
                    data_preview = excel.get('data_preview', {})
                    if data_preview:
                        att_line += f"\n  Contains pricing/specification data"
                
                attachments_summary_parts.append(att_line)
            
            attachments_summary = "\n".join(attachments_summary_parts) if attachments_summary_parts else "No attachments"
            
            # Create AI prompt
            prompt = f"""You are analyzing a vendor quotation email against project material benchmarks.

PROJECT BENCHMARKS ({len(benchmarks)} items):
{benchmark_summary}

VENDOR EMAIL:
Subject: {email_subject}

Body:
{email_body}

Attachments:
{attachments_summary}

ANALYSIS REQUIRED:
Analyze this vendor's quotation email and provide a comprehensive evaluation:

1. Overall Summary: Write a user-friendly summary (2-3 paragraphs) that helps decision-makers understand:
   - What materials/services this vendor is offering
   - How well their offerings match the project benchmarks
   - Key strengths and weaknesses of this vendor
   - Whether this vendor should be considered for selection

2. Benchmark-by-Benchmark Analysis: For EACH benchmark item, evaluate:
   - Does the vendor provide this item? (vendor_provides: true/false)
   - Score (0-10): How well does the vendor address this specific benchmark?
   - Detailed reasoning explaining the score
   - Any specific concerns or highlights

3. Scoring Metrics (0-10 scale):
   - overall_score: Overall vendor performance considering all factors
   - vendor_coverage: Percentage (0-100) of benchmarks the vendor can supply
   - response_speed_score: How well delivery timelines match requirements
   - quality_match_score: How well quality standards match benchmarks
   - pricing_competitiveness: How competitive the pricing appears (if mentioned)
   - professionalism_score: Email quality, completeness, and professionalism

Respond ONLY with valid JSON in this exact format:
{{
  "overall_summary": "string (detailed, user-friendly summary)",
  "overall_score": number,
  "vendor_coverage": number,
  "response_speed_score": number,
  "quality_match_score": number,
  "pricing_competitiveness": number,
  "professionalism_score": number,
  "benchmark_scores": [
    {{
      "benchmark_material_id": number,
      "category": "string",
      "benchmark_description": "string",
      "score": number,
      "reasoning": "string (detailed explanation)",
      "vendor_provides": boolean,
      "vendor_details": "string (what vendor offers for this item, if anything)"
    }}
  ]
}}"""

            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert procurement analyst specializing in construction materials. Analyze vendor quotations against project benchmarks and provide detailed, actionable scoring that helps users select the best vendor. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"AI analysis completed. Overall score: {result.get('overall_score', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            # Return default structure on error
            return {
                "overall_summary": f"Error analyzing email: {str(e)}",
                "overall_score": 0,
                "vendor_coverage": 0,
                "response_speed_score": 0,
                "quality_match_score": 0,
                "pricing_competitiveness": 0,
                "professionalism_score": 0,
                "benchmark_scores": [
                    {
                        "benchmark_material_id": bm["benchmark_material_id"],
                        "category": bm["category"],
                        "benchmark_description": bm["description"],
                        "score": 0,
                        "reasoning": "Analysis failed",
                        "vendor_provides": False,
                        "vendor_details": "N/A"
                    }
                    for bm in benchmarks
                ]
            }
    
    def _format_benchmarks_for_ai(self, benchmarks: List[Dict[str, Any]]) -> str:
        """Format benchmarks into a readable string for AI analysis."""
        formatted = []
        for bm in benchmarks:
            formatted.append(
                f"ID: {bm['benchmark_material_id']} | "
                f"Category: {bm['category']} | "
                f"Description: {bm['description']} | "
                f"Required by: {bm['required_by'] or 'Not specified'}"
            )
        return "\n".join(formatted)
    
    def batch_analyze_emails(
        self,
        project_id: int,
        emails: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple vendor emails against project benchmarks.
        
        Args:
            project_id: Project ID
            emails: List of email dictionaries with keys: subject, body, attachments
            
        Returns:
            List of analysis results for each email
        """
        results = []
        
        for idx, email in enumerate(emails, 1):
            logger.info(f"Analyzing email {idx}/{len(emails)}: {email.get('subject', 'No subject')}")
            
            analysis = self.analyze_vendor_email(
                project_id=project_id,
                email_subject=email.get("subject", ""),
                email_body=email.get("body", ""),
                attachments_info=email.get("attachments", [])
            )
            
            results.append({
                "email_subject": email.get("subject"),
                "email_from": email.get("from"),
                "email_date": email.get("date"),
                "analysis": analysis
            })
        
        logger.info(f"Completed batch analysis of {len(emails)} emails")
        return results
    
    def get_top_vendors(
        self,
        project_id: int,
        emails: List[Dict[str, Any]],
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple vendor emails and return top N vendors by overall score.
        
        Args:
            project_id: Project ID
            emails: List of email dictionaries
            top_n: Number of top vendors to return
            
        Returns:
            List of top vendor analyses sorted by overall_score
        """
        analyses = self.batch_analyze_emails(project_id, emails)
        
        # Sort by overall score
        sorted_analyses = sorted(
            analyses,
            key=lambda x: x["analysis"].get("overall_score", 0),
            reverse=True
        )
        
        return sorted_analyses[:top_n]
