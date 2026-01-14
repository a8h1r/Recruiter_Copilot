"""
Snowflake Cloud Database Integration for Recruiter Copilot.

This module handles connections to Snowflake for production data storage.
Saves candidate analysis results to the cloud for persistence and reporting.
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Try to import snowflake - it's optional
try:
    import snowflake.connector
    from snowflake.connector import SnowflakeConnection
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    SnowflakeConnection = None
    print("⚠️ Snowflake connector not installed. Cloud storage disabled.")

load_dotenv()


class SnowflakeDB:
    """
    Snowflake database client for storing candidate analysis data.
    """
    
    def __init__(self):
        """Initialize Snowflake connection parameters from environment."""
        self.account = os.getenv("SNOWFLAKE_ACCOUNT", "")
        self.user = os.getenv("SNOWFLAKE_USER", "")
        self.password = os.getenv("SNOWFLAKE_PASSWORD", "")
        self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "RECRUITER_WH")
        self.database = os.getenv("SNOWFLAKE_DATABASE", "RECRUITER_DB")
        self.schema = os.getenv("SNOWFLAKE_SCHEMA", "DATA")
        
        self._connection: Optional[SnowflakeConnection] = None
    
    def connect(self):
        """Establish connection to Snowflake."""
        if not SNOWFLAKE_AVAILABLE:
            raise RuntimeError("Snowflake connector not installed")
        
        if self._connection is None or self._connection.is_closed():
            self._connection = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema
            )
        return self._connection
    
    def close(self):
        """Close the Snowflake connection."""
        if self._connection and not self._connection.is_closed():
            self._connection.close()
    
    def ensure_table_exists(self):
        """Create the candidates table if it doesn't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS CANDIDATES (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255),
                    email VARCHAR(255),
                    resume_text TEXT,
                    github_url VARCHAR(500),
                    linkedin_url VARCHAR(500),
                    total_score FLOAT,
                    tier VARCHAR(20),
                    reasoning_summary TEXT,
                    verified_skills VARIANT,
                    flags VARIANT,
                    detailed_breakdown VARIANT,
                    full_report VARIANT,
                    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """)
            conn.commit()
        finally:
            cursor.close()
    
    def save_candidate(
        self,
        candidate_id: str,
        name: Optional[str],
        email: Optional[str],
        resume_text: Optional[str],
        github_url: Optional[str],
        linkedin_url: Optional[str],
        total_score: float,
        reasoning_summary: str,
        verified_skills: list,
        flags: list,
        detailed_breakdown: dict,
        full_report: dict
    ) -> bool:
        """
        Save a candidate analysis result to Snowflake.
        
        Args:
            candidate_id: Unique candidate identifier
            name: Candidate name
            email: Candidate email
            resume_text: Extracted resume text
            github_url: GitHub profile URL
            linkedin_url: LinkedIn profile URL
            total_score: Overall alignment score (0-10)
            reasoning_summary: AI-generated summary
            verified_skills: List of verified skills
            flags: Validation flags
            detailed_breakdown: Score breakdown
            full_report: Complete report JSON
            
        Returns:
            True if saved successfully
        """
        import json
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Determine tier based on score
        if total_score >= 8.5:
            tier = "TIER_1"
        elif total_score >= 7.0:
            tier = "TIER_2"
        elif total_score >= 5.5:
            tier = "TIER_3"
        else:
            tier = "TIER_4"
        
        try:
            cursor.execute("""
                INSERT INTO CANDIDATES (
                    CANDIDATE_ID, APPLICANT_NAME, EMAIL, RESUME_TEXT, GITHUB_URL, LINKEDIN_URL,
                    TOTAL_SCORE, TIER, REASONING_SUMMARY, VERIFIED_SKILLS,
                    FLAGS, DETAILED_BREAKDOWN, FULL_REPORT
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s))
            """, (
                candidate_id,
                name,
                email,
                resume_text,
                github_url,
                linkedin_url,
                total_score,
                tier,
                reasoning_summary,
                json.dumps(verified_skills),
                json.dumps(flags),
                json.dumps(detailed_breakdown),
                json.dumps(full_report, default=str)
            ))
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving to Snowflake: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a candidate by ID."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM CANDIDATES WHERE id = %s
            """, (candidate_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        finally:
            cursor.close()
    
    def get_top_candidates(self, limit: int = 10) -> list:
        """Get top scoring candidates."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, name, email, total_score, tier, reasoning_summary
                FROM CANDIDATES
                ORDER BY total_score DESC
                LIMIT %s
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
    
    def get_tier1_candidates(self) -> list:
        """Get all Tier 1 candidates (score >= 8.5)."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, name, email, total_score, reasoning_summary, verified_skills
                FROM CANDIDATES
                WHERE tier = 'TIER_1'
                ORDER BY total_score DESC
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        finally:
            cursor.close()


# Singleton instance
_snowflake_db: Optional[SnowflakeDB] = None


def get_snowflake_db() -> SnowflakeDB:
    """Get the Snowflake database instance."""
    global _snowflake_db
    if _snowflake_db is None:
        _snowflake_db = SnowflakeDB()
    return _snowflake_db
