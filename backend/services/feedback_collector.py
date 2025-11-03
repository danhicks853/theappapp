"""
Feedback Collector Service

Collects and analyzes human feedback from gate resolutions for prompt optimization.
Identifies patterns in rejections and approvals to improve agent prompts over time.
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Service for collecting and analyzing human feedback for prompt optimization.
    
    Features:
    - Collect feedback from gate resolutions
    - Analyze patterns in rejections and approvals
    - Identify common issues requiring prompt improvements
    - Generate actionable insights for prompt engineering
    
    Example:
        collector = FeedbackCollector(engine)
        await collector.collect_feedback(
            gate_id="gate-123",
            feedback_type="rejection",
            feedback_text="Agent didn't consider error handling",
            tags=["error_handling", "completeness"]
        )
        insights = await collector.get_feedback_insights("backend_dev")
    """
    
    def __init__(self, engine: Engine):
        """Initialize feedback collector with database engine."""
        self.engine = engine
        logger.info("FeedbackCollector initialized")
    
    async def collect_feedback(
        self,
        gate_id: str,
        feedback_type: str,
        feedback_text: str,
        agent_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collect feedback from a gate resolution.
        
        Args:
            gate_id: Gate identifier that generated this feedback
            feedback_type: Type of feedback ('approval', 'rejection', 'revision_request')
            feedback_text: The actual feedback text from the user
            agent_type: Type of agent (for filtering insights)
            tags: Optional tags for categorization (e.g., ['error_handling', 'security'])
            metadata: Additional context as JSON
        
        Returns:
            Feedback ID
        """
        logger.info(f"Collecting feedback for gate: {gate_id}, type={feedback_type}")
        import json
        
        query = text("""
            INSERT INTO feedback_logs 
            (gate_id, feedback_type, feedback_text, agent_type, tags, metadata, created_at)
            VALUES (:gate_id, :feedback_type, :feedback_text, :agent_type, :tags, :metadata, NOW())
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "gate_id": gate_id,
                "feedback_type": feedback_type,
                "feedback_text": feedback_text,
                "agent_type": agent_type,
                "tags": json.dumps(tags) if tags else None,
                "metadata": json.dumps(metadata) if metadata else None
            })
            conn.commit()
            
            feedback_id = str(result.scalar())
            logger.info(f"Feedback collected: id={feedback_id}")
            return feedback_id
    
    async def get_feedback_by_agent(
        self,
        agent_type: str,
        feedback_type: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get feedback for a specific agent type.
        
        Args:
            agent_type: Agent type to filter by
            feedback_type: Optional filter by feedback type
            days: Number of days to look back (default 30)
        
        Returns:
            List of feedback entries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        if feedback_type:
            query = text("""
                SELECT id, gate_id, feedback_type, feedback_text, agent_type, 
                       tags, metadata, created_at
                FROM feedback_logs
                WHERE agent_type = :agent_type 
                  AND feedback_type = :feedback_type
                  AND created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            params = {
                "agent_type": agent_type,
                "feedback_type": feedback_type,
                "cutoff_date": cutoff_date
            }
        else:
            query = text("""
                SELECT id, gate_id, feedback_type, feedback_text, agent_type,
                       tags, metadata, created_at
                FROM feedback_logs
                WHERE agent_type = :agent_type
                  AND created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            params = {
                "agent_type": agent_type,
                "cutoff_date": cutoff_date
            }
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            
            feedback_list = [
                {
                    "id": str(row[0]),
                    "gate_id": str(row[1]),
                    "feedback_type": row[2],
                    "feedback_text": row[3],
                    "agent_type": row[4],
                    "tags": row[5],
                    "metadata": row[6],
                    "created_at": row[7].isoformat() if row[7] else None
                }
                for row in rows
            ]
            
            logger.info(f"Retrieved {len(feedback_list)} feedback entries for {agent_type}")
            return feedback_list
    
    async def analyze_patterns(
        self,
        agent_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze feedback patterns to identify common issues.
        
        Args:
            agent_type: Optional agent type to filter by
            days: Number of days to analyze (default 30)
        
        Returns:
            Dict with pattern analysis including:
            - common_rejection_reasons
            - most_frequent_tags
            - approval_rate
            - revision_rate
            - actionable_insights
        """
        logger.info(f"Analyzing feedback patterns: agent_type={agent_type}, days={days}")
        
        # Get feedback data
        if agent_type:
            feedback_data = await self.get_feedback_by_agent(agent_type, days=days)
        else:
            # Get all feedback
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = text("""
                SELECT id, gate_id, feedback_type, feedback_text, agent_type,
                       tags, metadata, created_at
                FROM feedback_logs
                WHERE created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"cutoff_date": cutoff_date})
                rows = result.fetchall()
                
                feedback_data = [
                    {
                        "id": str(row[0]),
                        "gate_id": str(row[1]),
                        "feedback_type": row[2],
                        "feedback_text": row[3],
                        "agent_type": row[4],
                        "tags": row[5],
                        "metadata": row[6],
                        "created_at": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
        
        if not feedback_data:
            return {
                "total_feedback": 0,
                "message": "No feedback data available for analysis"
            }
        
        # Count feedback types
        feedback_types = Counter(f["feedback_type"] for f in feedback_data)
        total = len(feedback_data)
        
        # Aggregate tags
        all_tags = []
        for f in feedback_data:
            if f["tags"]:
                all_tags.extend(f["tags"])
        tag_counts = Counter(all_tags)
        
        # Extract rejection reasons (first sentence of rejection feedback)
        rejection_reasons = []
        for f in feedback_data:
            if f["feedback_type"] == "rejection" and f["feedback_text"]:
                # Get first sentence
                first_sentence = f["feedback_text"].split('.')[0].strip()
                if first_sentence:
                    rejection_reasons.append(first_sentence)
        
        reason_counts = Counter(rejection_reasons)
        
        # Calculate rates
        approval_rate = (feedback_types.get("approval", 0) / total * 100) if total > 0 else 0
        rejection_rate = (feedback_types.get("rejection", 0) / total * 100) if total > 0 else 0
        revision_rate = (feedback_types.get("revision_request", 0) / total * 100) if total > 0 else 0
        
        # Generate actionable insights
        insights = self._generate_insights(
            tag_counts=tag_counts,
            reason_counts=reason_counts,
            approval_rate=approval_rate,
            rejection_rate=rejection_rate
        )
        
        analysis = {
            "total_feedback": total,
            "feedback_by_type": dict(feedback_types),
            "approval_rate": round(approval_rate, 2),
            "rejection_rate": round(rejection_rate, 2),
            "revision_rate": round(revision_rate, 2),
            "most_common_tags": tag_counts.most_common(10),
            "common_rejection_reasons": reason_counts.most_common(5),
            "actionable_insights": insights,
            "analysis_period_days": days,
            "agent_type": agent_type
        }
        
        logger.info(f"Pattern analysis complete: {total} feedback entries analyzed")
        return analysis
    
    def _generate_insights(
        self,
        tag_counts: Counter,
        reason_counts: Counter,
        approval_rate: float,
        rejection_rate: float
    ) -> List[str]:
        """
        Generate actionable insights from pattern analysis.
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # Check approval rate
        if approval_rate < 50:
            insights.append(
                f"⚠️ Low approval rate ({approval_rate:.1f}%). "
                "Consider reviewing and improving agent prompts for better decision quality."
            )
        elif approval_rate > 80:
            insights.append(
                f"✅ High approval rate ({approval_rate:.1f}%). "
                "Agent prompts are performing well."
            )
        
        # Check common tags
        if tag_counts:
            top_tag, top_count = tag_counts.most_common(1)[0]
            if top_count > 3:
                insights.append(
                    f"📌 Frequent issue: '{top_tag}' mentioned {top_count} times. "
                    "Consider adding specific guidance in prompts to address this."
                )
        
        # Check common rejection reasons
        if reason_counts:
            top_reason, count = reason_counts.most_common(1)[0]
            if count > 2:
                insights.append(
                    f"🔄 Common rejection: '{top_reason}' ({count} times). "
                    "Update prompts to explicitly handle this scenario."
                )
        
        # General recommendations
        if rejection_rate > 30:
            insights.append(
                "💡 Recommendation: High rejection rate suggests prompts need more specificity. "
                "Add examples of good/bad outputs and clearer constraints."
            )
        
        return insights
    
    async def get_feedback_summary(
        self,
        agent_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get a quick summary of recent feedback.
        
        Args:
            agent_type: Optional agent type filter
            days: Number of days to summarize
        
        Returns:
            Summary dict with counts and trends
        """
        analysis = await self.analyze_patterns(agent_type, days)
        
        return {
            "period": f"Last {days} days",
            "total_feedback": analysis.get("total_feedback", 0),
            "approval_rate": analysis.get("approval_rate", 0),
            "top_issues": [tag for tag, _ in analysis.get("most_common_tags", [])[:3]],
            "key_insight": analysis.get("actionable_insights", [None])[0] if analysis.get("actionable_insights") else "No insights available yet"
        }
