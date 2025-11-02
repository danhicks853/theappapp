"""
Collaboration Orchestrator Service

Manages full lifecycle of agent-to-agent collaborations with database tracking.
Enhances the basic routing in Orchestrator with persistence and metrics.

Reference: Decision 70 - Agent Collaboration Protocol
"""
import logging
import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.models.collaboration import (
    CollaborationRequest,
    CollaborationResponse,
    CollaborationOutcome,
    CollaborationStatus,
    CollaborationRequestType,
    CollaborationUrgency
)

logger = logging.getLogger(__name__)


class CollaborationOrchestrator:
    """
    Manages agent-to-agent collaboration with full lifecycle tracking.
    
    Features:
    - Request validation and routing
    - Database persistence
    - Context curation
    - Response delivery
    - Outcome recording
    - Metrics tracking
    
    Example:
        orchestrator = CollaborationOrchestrator(engine)
        
        # Handle a help request
        result = await orchestrator.handle_help_request(
            requesting_agent_id="backend-1",
            question="How do I handle auth errors?",
            context={"error": "InvalidToken"},
            request_type=CollaborationRequestType.BUG_DEBUGGING
        )
    """
    
    def __init__(self, engine: Engine):
        """Initialize collaboration orchestrator."""
        self.engine = engine
        logger.info("CollaborationOrchestrator initialized")
    
    async def handle_help_request(
        self,
        requesting_agent_id: str,
        requesting_agent_type: str,
        question: str,
        context: Dict[str, Any],
        *,
        request_type: CollaborationRequestType = CollaborationRequestType.API_CLARIFICATION,
        urgency: CollaborationUrgency = CollaborationUrgency.NORMAL,
        suggested_specialist: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a collaboration request from an agent.
        
        Full workflow:
        1. Create CollaborationRequest
        2. Persist to DB (collaboration_requests table)
        3. Route to appropriate specialist
        4. Track in collaboration_exchanges
        5. Return routing result
        
        Args:
            requesting_agent_id: ID of agent needing help
            requesting_agent_type: Type of requesting agent
            question: The question or request
            context: Relevant context
            request_type: Type of collaboration
            urgency: How urgent
            suggested_specialist: Optional specialist hint
        
        Returns:
            Dict with collaboration_id, specialist info, status
        """
        # 1. Create structured request
        collaboration_id = str(uuid.uuid4())
        
        request = CollaborationRequest(
            collaboration_id=collaboration_id,
            request_type=request_type,
            requesting_agent_id=requesting_agent_id,
            requesting_agent_type=requesting_agent_type,
            question=question,
            context=context,
            suggested_specialist=suggested_specialist,
            urgency=urgency
        )
        
        logger.info(
            "Handling help request | collaboration_id=%s | from=%s | type=%s | urgency=%s",
            collaboration_id,
            requesting_agent_id,
            request_type,
            urgency
        )
        
        # 2. Persist to database
        await self._persist_request(request)
        
        # 3. Route to specialist
        specialist_info = await self._route_to_specialist(request)
        
        if not specialist_info.get("specialist_id"):
            # No specialist available
            logger.warning(
                "No specialist available | collaboration_id=%s",
                collaboration_id
            )
            
            await self._update_status(collaboration_id, CollaborationStatus.FAILED)
            
            return {
                "collaboration_id": collaboration_id,
                "status": "failed",
                "reason": "No suitable specialist available",
                "specialist_id": None
            }
        
        # 4. Track exchange (request sent)
        await self._track_exchange(
            collaboration_id=collaboration_id,
            from_agent=requesting_agent_id,
            to_agent=specialist_info["specialist_id"],
            message_type="request",
            content=question
        )
        
        # 5. Update status to routed
        await self._update_status(collaboration_id, CollaborationStatus.ROUTED)
        
        return {
            "collaboration_id": collaboration_id,
            "status": "routed",
            "specialist_id": specialist_info["specialist_id"],
            "specialist_type": specialist_info["specialist_type"],
            "routing_confidence": specialist_info.get("confidence", 0.8),
            "reasoning": specialist_info.get("reasoning", "")
        }
    
    async def deliver_response(
        self,
        collaboration_id: str,
        responding_specialist_id: str,
        responding_specialist_type: str,
        response: str,
        confidence: float = 0.8,
        *,
        reasoning: Optional[str] = None,
        suggested_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deliver specialist's response back to requesting agent.
        
        Args:
            collaboration_id: ID of collaboration
            responding_specialist_id: Who is responding
            responding_specialist_type: Type of specialist
            response: The answer/guidance
            confidence: Specialist's confidence (0-1)
            reasoning: Optional explanation
            suggested_actions: Optional next steps
        
        Returns:
            Dict with delivery status
        """
        logger.info(
            "Delivering response | collaboration_id=%s | from=%s | confidence=%.2f",
            collaboration_id,
            responding_specialist_id,
            confidence
        )
        
        # Create structured response
        collab_response = CollaborationResponse(
            collaboration_id=collaboration_id,
            responding_specialist_id=responding_specialist_id,
            responding_specialist_type=responding_specialist_type,
            response=response,
            confidence=confidence,
            reasoning=reasoning,
            suggested_actions=suggested_actions or []
        )
        
        # Get original request to find requester
        request_info = await self._get_request_info(collaboration_id)
        
        if not request_info:
            logger.error("Collaboration not found | collaboration_id=%s", collaboration_id)
            return {"status": "error", "message": "Collaboration not found"}
        
        # Track exchange (response delivered)
        await self._track_exchange(
            collaboration_id=collaboration_id,
            from_agent=responding_specialist_id,
            to_agent=request_info["requesting_agent_id"],
            message_type="response",
            content=response
        )
        
        # Update status
        await self._update_status(collaboration_id, CollaborationStatus.RESPONDED)
        
        # Store response details
        await self._store_response(collab_response)
        
        return {
            "status": "delivered",
            "collaboration_id": collaboration_id,
            "delivered_to": request_info["requesting_agent_id"],
            "confidence": confidence
        }
    
    async def record_outcome(
        self,
        collaboration_id: str,
        resolution: str,
        requester_satisfied: bool,
        *,
        valuable_for_rag: bool = False,
        lessons_learned: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record the final outcome of a collaboration.
        
        Args:
            collaboration_id: ID of collaboration
            resolution: How it was resolved
            requester_satisfied: Was the answer helpful?
            valuable_for_rag: Should this be saved for future?
            lessons_learned: Key takeaways
        
        Returns:
            Dict with outcome recording status
        """
        logger.info(
            "Recording outcome | collaboration_id=%s | satisfied=%s | valuable=%s",
            collaboration_id,
            requester_satisfied,
            valuable_for_rag
        )
        
        # Calculate response time
        request_info = await self._get_request_info(collaboration_id)
        response_time = None
        
        if request_info and request_info.get("created_at"):
            time_diff = datetime.now(UTC) - request_info["created_at"]
            response_time = time_diff.total_seconds()
        
        # Create outcome
        outcome = CollaborationOutcome(
            collaboration_id=collaboration_id,
            status=CollaborationStatus.RESOLVED if requester_satisfied else CollaborationStatus.FAILED,
            resolution=resolution,
            requester_satisfied=requester_satisfied,
            valuable_for_rag=valuable_for_rag,
            response_time_seconds=response_time,
            lessons_learned=lessons_learned
        )
        
        # Persist outcome
        await self._persist_outcome(outcome)
        
        # Update status
        final_status = CollaborationStatus.RESOLVED if requester_satisfied else CollaborationStatus.FAILED
        await self._update_status(collaboration_id, final_status)
        
        return {
            "status": "recorded",
            "collaboration_id": collaboration_id,
            "final_status": final_status.value,
            "response_time_seconds": response_time
        }
    
    async def _persist_request(self, request: CollaborationRequest) -> None:
        """Persist collaboration request to database."""
        query = text("""
            INSERT INTO collaboration_requests 
            (id, request_type, requesting_agent_id, requesting_agent_type, question, 
             context, suggested_specialist, urgency, status, created_at)
            VALUES 
            (:id, :request_type, :requesting_agent_id, :requesting_agent_type, :question,
             :context, :suggested_specialist, :urgency, :status, :created_at)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": request.collaboration_id,
                "request_type": request.request_type.value,
                "requesting_agent_id": request.requesting_agent_id,
                "requesting_agent_type": request.requesting_agent_type,
                "question": request.question,
                "context": str(request.context),  # JSON string
                "suggested_specialist": request.suggested_specialist,
                "urgency": request.urgency.value,
                "status": CollaborationStatus.PENDING.value,
                "created_at": request.timestamp
            })
            conn.commit()
    
    async def _route_to_specialist(self, request: CollaborationRequest) -> Dict[str, Any]:
        """
        Route request to appropriate specialist.
        
        Enhanced routing with expertise mapping.
        """
        # Expertise mapping based on request type
        expertise_map = {
            CollaborationRequestType.SECURITY_REVIEW: ["security_expert", "backend_developer"],
            CollaborationRequestType.API_CLARIFICATION: ["backend_developer", "frontend_developer"],
            CollaborationRequestType.BUG_DEBUGGING: ["backend_developer", "qa_engineer"],
            CollaborationRequestType.INFRASTRUCTURE: ["devops_engineer", "backend_developer"],
            CollaborationRequestType.MODEL_DATA: ["backend_developer", "workshopper"],
            CollaborationRequestType.REQUIREMENTS: ["project_manager", "workshopper"]
        }
        
        candidate_types = expertise_map.get(request.request_type, ["backend_developer"])
        
        # For now, return first candidate (in real system, check availability)
        selected_type = candidate_types[0]
        
        # Generate mock specialist ID (in real system, query active agents)
        specialist_id = f"{selected_type}-1"
        
        return {
            "specialist_id": specialist_id,
            "specialist_type": selected_type,
            "confidence": 0.85,
            "reasoning": f"Routed to {selected_type} based on request type {request.request_type.value}"
        }
    
    async def _track_exchange(
        self,
        collaboration_id: str,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: str
    ) -> None:
        """Track message exchange in collaboration."""
        query = text("""
            INSERT INTO collaboration_exchanges
            (id, collaboration_id, from_agent_id, to_agent_id, message_type, content, timestamp)
            VALUES
            (:id, :collaboration_id, :from_agent, :to_agent, :message_type, :content, :timestamp)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": str(uuid.uuid4()),
                "collaboration_id": collaboration_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                "content": content[:1000],  # Limit content length
                "timestamp": datetime.now(UTC)
            })
            conn.commit()
    
    async def _update_status(self, collaboration_id: str, status: CollaborationStatus) -> None:
        """Update collaboration status."""
        query = text("""
            UPDATE collaboration_requests
            SET status = :status, updated_at = :updated_at
            WHERE id = :id
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": collaboration_id,
                "status": status.value,
                "updated_at": datetime.now(UTC)
            })
            conn.commit()
    
    async def _get_request_info(self, collaboration_id: str) -> Optional[Dict[str, Any]]:
        """Get collaboration request info from database."""
        query = text("""
            SELECT requesting_agent_id, created_at
            FROM collaboration_requests
            WHERE id = :id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"id": collaboration_id})
            row = result.fetchone()
            
            if row:
                return {
                    "requesting_agent_id": row[0],
                    "created_at": row[1]
                }
            return None
    
    async def _store_response(self, response: CollaborationResponse) -> None:
        """Store response details in database."""
        query = text("""
            INSERT INTO collaboration_responses
            (id, collaboration_id, responding_specialist_id, responding_specialist_type,
             response, confidence, reasoning, timestamp)
            VALUES
            (:id, :collaboration_id, :specialist_id, :specialist_type, :response,
             :confidence, :reasoning, :timestamp)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": str(uuid.uuid4()),
                "collaboration_id": response.collaboration_id,
                "specialist_id": response.responding_specialist_id,
                "specialist_type": response.responding_specialist_type,
                "response": response.response,
                "confidence": response.confidence,
                "reasoning": response.reasoning,
                "timestamp": response.timestamp
            })
            conn.commit()
    
    async def _persist_outcome(self, outcome: CollaborationOutcome) -> None:
        """Persist collaboration outcome to database."""
        query = text("""
            INSERT INTO collaboration_outcomes
            (id, collaboration_id, status, resolution, requester_satisfied,
             valuable_for_rag, response_time_seconds, lessons_learned, timestamp)
            VALUES
            (:id, :collaboration_id, :status, :resolution, :satisfied,
             :valuable, :response_time, :lessons, :timestamp)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": str(uuid.uuid4()),
                "collaboration_id": outcome.collaboration_id,
                "status": outcome.status.value,
                "resolution": outcome.resolution,
                "satisfied": outcome.requester_satisfied,
                "valuable": outcome.valuable_for_rag,
                "response_time": outcome.response_time_seconds,
                "lessons": outcome.lessons_learned,
                "timestamp": outcome.timestamp
            })
            conn.commit()
    
    async def detect_collaboration_loop(
        self,
        agent_a_id: str,
        agent_b_id: str,
        current_question: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if two agents are in a collaboration loop.
        
        A loop occurs when Agent A asks Agent B, then B asks A about
        the same topic, repeatedly (3+ cycles).
        
        Args:
            agent_a_id: First agent in potential loop
            agent_b_id: Second agent in potential loop
            current_question: The current question being asked
        
        Returns:
            Loop details if detected, None otherwise
        """
        # Query recent collaborations between these agents
        query = text("""
            SELECT cr.question, cr.created_at
            FROM collaboration_requests cr
            WHERE (cr.requesting_agent_id = :agent_a AND :agent_b IN (
                SELECT specialist_id FROM collaboration_responses 
                WHERE collaboration_id = cr.id
            ))
            OR (cr.requesting_agent_id = :agent_b AND :agent_a IN (
                SELECT specialist_id FROM collaboration_responses
                WHERE collaboration_id = cr.id
            ))
            ORDER BY cr.created_at DESC
            LIMIT 10
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "agent_a": agent_a_id,
                "agent_b": agent_b_id
            })
            recent_questions = [row[0] for row in result.fetchall()]
        
        if len(recent_questions) < 3:
            # Not enough history to detect loop
            return None
        
        # Simple similarity check (keyword-based for now)
        # In production, use embeddings for semantic similarity
        similar_count = sum(
            1 for q in recent_questions 
            if self._calculate_similarity(current_question, q) > 0.85
        )
        
        if similar_count >= 2:
            # Loop detected! 3rd occurrence of similar question
            loop_id = str(uuid.uuid4())
            
            logger.warning(
                "Collaboration loop detected | loop_id=%s | agents=%s<->%s | cycles=%d",
                loop_id,
                agent_a_id,
                agent_b_id,
                similar_count + 1
            )
            
            # Record the loop
            await self._record_loop(
                loop_id=loop_id,
                agent_a_id=agent_a_id,
                agent_b_id=agent_b_id,
                questions=[current_question] + recent_questions[:similar_count],
                cycle_count=similar_count + 1,
                similarity=0.85  # From threshold
            )
            
            return {
                "loop_detected": True,
                "loop_id": loop_id,
                "cycle_count": similar_count + 1,
                "agents": [agent_a_id, agent_b_id],
                "similar_questions": recent_questions[:similar_count],
                "action_required": "create_gate"
            }
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.
        
        Simple keyword-based approach for now.
        TODO: Replace with embedding-based similarity for production.
        """
        # Normalize and tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    async def _record_loop(
        self,
        loop_id: str,
        agent_a_id: str,
        agent_b_id: str,
        questions: List[str],
        cycle_count: int,
        similarity: float
    ) -> None:
        """Record a detected collaboration loop in the database."""
        query = text("""
            INSERT INTO collaboration_loops
            (id, agent_a_id, agent_b_id, topic_similarity, cycle_count, 
             questions, detected_at, gate_created)
            VALUES
            (:id, :agent_a, :agent_b, :similarity, :cycles, :questions, :detected_at, :gate_created)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": loop_id,
                "agent_a": agent_a_id,
                "agent_b": agent_b_id,
                "similarity": similarity,
                "cycles": cycle_count,
                "questions": str(questions[:5]),  # Store first 5 questions
                "detected_at": datetime.now(UTC),
                "gate_created": False  # Will be updated when gate is created
            })
            conn.commit()
    
    async def get_collaboration_metrics(
        self,
        agent_pair: Optional[str] = None,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get collaboration metrics.
        
        Args:
            agent_pair: Optional filter like "backend_dev->security_expert"
            time_range_hours: Time range for metrics
        
        Returns:
            Dict with metrics data
        """
        # Query collaboration outcomes
        time_filter = f"AND co.timestamp > NOW() - INTERVAL '{time_range_hours} hours'"
        
        query = text(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN co.requester_satisfied = true THEN 1 ELSE 0 END) as successful,
                AVG(co.response_time_seconds) as avg_response_time,
                SUM(co.tokens_used) as total_tokens
            FROM collaboration_outcomes co
            JOIN collaboration_requests cr ON co.collaboration_id = cr.id
            WHERE 1=1 {time_filter}
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            
            if row:
                total = row[0] or 0
                successful = row[1] or 0
                
                return {
                    "total_collaborations": total,
                    "successful_count": successful,
                    "failed_count": total - successful,
                    "success_rate": successful / total if total > 0 else 0.0,
                    "average_response_time_seconds": row[2],
                    "total_tokens_used": row[3] or 0,
                    "time_range_hours": time_range_hours
                }
        
        return {
            "total_collaborations": 0,
            "success_rate": 0.0,
            "time_range_hours": time_range_hours
        }
    
    async def detect_semantic_loop(
        self,
        agent_a_id: str,
        agent_b_id: str,
        current_question: str,
        *,
        similarity_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        Detect collaboration loops using semantic similarity.
        
        Uses embeddings to detect when agents ask each other similar questions
        repeatedly, indicating they're stuck in a collaboration loop.
        
        Args:
            agent_a_id: First agent in potential loop
            agent_b_id: Second agent in potential loop
            current_question: The current question being asked
            similarity_threshold: Cosine similarity threshold (default 0.85)
        
        Returns:
            Loop details if detected, None otherwise
        
        Example:
            loop = await orchestrator.detect_semantic_loop(
                agent_a_id="backend-1",
                agent_b_id="security-1",
                current_question="How do I handle CORS?"
            )
        """
        # Query recent collaborations between these agents
        query = text("""
            SELECT cr.question, cr.created_at
            FROM collaboration_requests cr
            WHERE (cr.requesting_agent_id = :agent_a OR cr.requesting_agent_id = :agent_b)
            AND cr.created_at > NOW() - INTERVAL '24 hours'
            ORDER BY cr.created_at DESC
            LIMIT 10
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "agent_a": agent_a_id,
                "agent_b": agent_b_id
            })
            recent_questions = [row[0] for row in result.fetchall()]
        
        if len(recent_questions) < 2:
            # Not enough history
            return None
        
        # Calculate semantic similarity with recent questions
        # For now, use simple text similarity (Jaccard)
        # In production, replace with embeddings (OpenAI, sentence-transformers, etc.)
        similar_count = 0
        similar_questions = []
        
        for past_question in recent_questions:
            similarity = self._calculate_text_similarity(current_question, past_question)
            
            if similarity >= similarity_threshold:
                similar_count += 1
                similar_questions.append(past_question)
        
        # Loop detected if 2+ similar questions
        if similar_count >= 2:
            loop_id = str(uuid.uuid4())
            
            logger.warning(
                "Semantic collaboration loop detected | loop_id=%s | agents=%s<->%s | similar_count=%d",
                loop_id,
                agent_a_id,
                agent_b_id,
                similar_count
            )
            
            # Record the loop
            await self._record_semantic_loop(
                loop_id=loop_id,
                agent_a_id=agent_a_id,
                agent_b_id=agent_b_id,
                questions=[current_question] + similar_questions,
                similarity_score=similarity_threshold
            )
            
            return {
                "loop_detected": True,
                "loop_id": loop_id,
                "cycle_count": similar_count + 1,
                "agents": [agent_a_id, agent_b_id],
                "similar_questions": similar_questions,
                "similarity_threshold": similarity_threshold,
                "action_required": "create_gate"
            }
        
        return None
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Current implementation uses Jaccard similarity (word overlap).
        TODO: Replace with embedding-based similarity for production:
        - OpenAI embeddings (ada-002)
        - Sentence-transformers
        - Or other embedding models
        """
        # Normalize and tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    async def _calculate_embedding_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Calculate cosine similarity using embeddings.
        
        This is the production-ready version that should be used
        when OpenAI adapter is available.
        
        TODO: Implement when needed:
        1. Generate embeddings for both texts
        2. Calculate cosine similarity
        3. Return score 0-1
        """
        # Placeholder for embedding-based similarity
        # Would use OpenAI adapter or sentence-transformers
        
        # import numpy as np
        # embedding1 = await self.get_embedding(text1)
        # embedding2 = await self.get_embedding(text2)
        # similarity = np.dot(embedding1, embedding2)
        
        return 0.0  # Placeholder
    
    async def _record_semantic_loop(
        self,
        loop_id: str,
        agent_a_id: str,
        agent_b_id: str,
        questions: list,
        similarity_score: float
    ) -> None:
        """Record a detected semantic collaboration loop."""
        query = text("""
            INSERT INTO collaboration_loops
            (id, agent_a_id, agent_b_id, topic_similarity, cycle_count,
             questions, detected_at, gate_created)
            VALUES
            (:id, :agent_a, :agent_b, :similarity, :cycles, :questions, :detected_at, :gate_created)
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": loop_id,
                "agent_a": agent_a_id,
                "agent_b": agent_b_id,
                "similarity": similarity_score,
                "cycles": len(questions),
                "questions": str(questions[:5]),  # Store first 5
                "detected_at": datetime.now(UTC),
                "gate_created": False
            })
            conn.commit()
