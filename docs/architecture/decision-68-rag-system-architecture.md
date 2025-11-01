# Decision 68: RAG System Architecture

## Status
✅ **RESOLVED**  
**Date**: Nov 1, 2025  
**Priority**: P0 - BLOCKING

---

## Context

The RAG (Retrieval-Augmented Generation) system enables learning from past projects. Based on Decision 67, orchestrator mediates all RAG access - agents never query RAG directly.

---

## Decision Summary

### **1. Knowledge Storage: Curated with Learning Focus**

**What Gets Embedded**:
1. **Failed Tests/Tasks + Solutions** - Any test/task failure with verified resolution
2. **Human Gate Rejections + Feedback** - Rejection reason and approved revision
3. **First-Attempt Gate Approvals** - Gold standard patterns that worked perfectly

**Rationale**: High signal-to-noise, cost-effective, focus on problem-solving patterns

---

### **2. Embedding Timing: Checkpoint-Based**

**Implementation**:
- NOT real-time during active work
- Batch at checkpoints: Phase completion, project completion, cancellation, manual trigger
- Future-focused: Benefits future projects, not current one

**Process**:
1. Collect qualifying knowledge since last checkpoint
2. Batch generate embeddings (OpenAI text-embedding-3-small)
3. Store in Qdrant with metadata

**Rationale**: No flow interruption, simpler implementation, complete context available

---

### **3. Query Strategy: Orchestrator-Mediated with Structured Presentation**

**Query Interface**:
- Only orchestrator queries RAG (agents never access directly)
- Orchestrator filters and injects relevant knowledge into agent context

**Query Parameters**:
- Semantic search for similar patterns
- Orchestrator-driven filters (task type, agent type, technology)
- Success-only verified patterns
- No recency bias (timeless problem-solving)
- 3-5 examples if available and relevant

**Conflicting Patterns**: Provide top 2-3 with structured presentation

**Format to Prevent Agent Confusion**:
```
[ORCHESTRATOR CONTEXT: Historical Knowledge]

Similar situations have been resolved these ways:

Pattern 1 (Most Common - 5 successes):
- Problem: [description]
- Solution: [specific steps]
- When to try: [decision criteria]

Pattern 2 (Moderate - 3 successes):
- Problem: [description]
- Solution: [specific steps]
- When to try: [decision criteria]

Pattern 3 (Less Common - 1 success):
- Problem: [description]
- Solution: [specific steps]
- When to try: [decision criteria]

Recommendation: Try patterns in order. Pattern 1 is most likely based on historical data.

[END CONTEXT]
```

**Rationale**: Clear structure, agent retains autonomy, transparency in success rates

---

### **4. Knowledge Lifecycle Management**

**Quality Indicators**:
- Failed test/task + solution: HIGH (verified success)
- Human gate rejection + resolution: HIGHEST (human wisdom)
- First-attempt gate approval: HIGHEST (gold standard)

**Retention Policy**:
- **1 year** from embedding date
- Automatic deletion after 1 year
- No archive (keeps system clean)

**Rationale**: 
- Natural tech evolution handling
- Prevents version fragmentation
- Accommodates rapidly advancing AI technology
- Simple automatic cleanup

**Conflicting Patterns**:
- Provide top 2-3 alternatives ranked by success rate
- Let orchestrator choose most relevant for specific situation

---

## Implementation Components

### **1. Knowledge Capture Service**

```python
class KnowledgeCaptureService:
    """Captures learning moments during project execution."""
    
    async def capture_failure_solution(
        self, project_id, agent_type, task_type,
        failure_description, error_message, solution_steps, technology
    ):
        """Capture failed test/task with verified resolution."""
        entry = KnowledgeEntry(
            entry_type="failure_solution",
            project_id=project_id,
            agent_type=agent_type,
            failure_description=failure_description,
            solution_steps=solution_steps,
            success_verified=True
        )
        await self._stage_for_embedding(entry)
    
    async def capture_gate_rejection(
        self, project_id, gate_type, human_feedback, revision_approach
    ):
        """Capture human gate rejection with feedback."""
        entry = KnowledgeEntry(
            entry_type="gate_rejection",
            gate_type=gate_type,
            human_feedback=human_feedback,
            revision_approach=revision_approach
        )
        await self._stage_for_embedding(entry)
    
    async def capture_gate_approval(
        self, project_id, gate_type, approved_approach
    ):
        """Capture first-attempt gate approval (gold standard)."""
        entry = KnowledgeEntry(
            entry_type="gate_approval",
            gate_type=gate_type,
            approved_approach=approved_approach
        )
        await self._stage_for_embedding(entry)
```

### **2. Checkpoint Embedding Service**

```python
class CheckpointEmbeddingService:
    """Processes staged knowledge at checkpoints and embeds in Qdrant."""
    
    async def process_checkpoint(self, project_id, checkpoint_type):
        """Batch process all staged knowledge for a project."""
        staged_entries = await self.db.fetch_staged(project_id)
        
        for entry in staged_entries:
            # Generate embedding
            text = self._format_entry_for_embedding(entry)
            embedding = await self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            # Store in Qdrant
            await self.qdrant.upsert(
                collection_name="project_knowledge",
                points=[{
                    "id": entry.id,
                    "vector": embedding.data[0].embedding,
                    "payload": {
                        "entry_type": entry.entry_type,
                        "agent_type": entry.agent_type,
                        "task_type": entry.task_type,
                        "text": text,
                        "success_count": 1,
                        "embedded_at": datetime.now().isoformat()
                    }
                }]
            )
```

### **3. RAG Query Service**

```python
class RAGQueryService:
    """Orchestrator-only service for querying RAG knowledge."""
    
    async def query_for_task(
        self, task_description, agent_type, task_type, technology, max_results=5
    ) -> List[RAGPattern]:
        """Query RAG for relevant patterns before task assignment."""
        query_embedding = await self._generate_embedding(task_description)
        
        results = await self.qdrant.search(
            collection_name="project_knowledge",
            query_vector=query_embedding,
            query_filter={
                "agent_type": agent_type,
                "task_type": task_type
            },
            limit=max_results,
            score_threshold=0.7
        )
        
        patterns = [self._format_as_pattern(r) for r in results]
        return self._rank_patterns(patterns)[:5]
    
    async def query_for_failure(
        self, failure_description, error_message, agent_type, task_type
    ) -> List[RAGPattern]:
        """Query RAG for similar failure resolutions."""
        query_text = f"Failure: {failure_description}\nError: {error_message}"
        query_embedding = await self._generate_embedding(query_text)
        
        results = await self.qdrant.search(
            collection_name="project_knowledge",
            query_vector=query_embedding,
            query_filter={
                "entry_type": "failure_solution",
                "agent_type": agent_type
            },
            limit=5,
            score_threshold=0.75
        )
        
        patterns = [self._format_as_pattern(r) for r in results]
        return self._rank_patterns(patterns)[:3]
```

### **4. Orchestrator Context Builder**

```python
class OrchestratorContextBuilder:
    """Builds agent context with orchestrator-filtered RAG knowledge."""
    
    async def build_context_for_task(self, task, agent_type) -> str:
        """Build agent context with RAG knowledge injection."""
        patterns = await self.rag.query_for_task(
            task.description, agent_type, task.type, task.technology
        )
        
        if not patterns:
            return self._build_basic_context(task)
        
        rag_context = self._format_patterns_for_agent(patterns)
        return f"{self._build_basic_context(task)}\n\n{rag_context}"
    
    def _format_patterns_for_agent(self, patterns: List[RAGPattern]) -> str:
        """Format RAG patterns to avoid agent confusion."""
        context = "[ORCHESTRATOR CONTEXT: Historical Knowledge]\n\n"
        context += "Similar situations have been resolved these ways:\n\n"
        
        for i, pattern in enumerate(patterns[:3], 1):
            success_label = (
                "Most Common" if pattern.success_count >= 5
                else "Moderate" if pattern.success_count >= 3
                else "Less Common"
            )
            
            context += f"Pattern {i} ({success_label} - {pattern.success_count} successes):\n"
            context += f"- Problem: {pattern.problem}\n"
            context += f"- Solution: {pattern.solution}\n"
            context += f"- When to try: {pattern.when_to_try}\n\n"
        
        context += "Recommendation: Try patterns in order. Pattern 1 is most likely.\n"
        context += "\n[END CONTEXT]\n"
        return context
```

### **5. Knowledge Pruning Service**

```python
class KnowledgePruningService:
    """Automatically prunes knowledge older than 1 year."""
    
    async def prune_old_knowledge(self) -> int:
        """Delete knowledge embedded more than 1 year ago."""
        cutoff_date = datetime.now() - timedelta(days=365)
        
        all_points = await self.qdrant.scroll(
            collection_name="project_knowledge",
            limit=10000
        )
        
        points_to_delete = [
            point.id for point in all_points[0]
            if datetime.fromisoformat(point.payload['embedded_at']) < cutoff_date
        ]
        
        if points_to_delete:
            await self.qdrant.delete(
                collection_name="project_knowledge",
                points_selector={"points": points_to_delete}
            )
        
        return len(points_to_delete)
```

---

## Database Schema

### **Knowledge Staging Table**

```sql
CREATE TABLE knowledge_staging (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_type VARCHAR(50) NOT NULL,
    project_id UUID REFERENCES projects(id),
    agent_type VARCHAR(100) NOT NULL,
    task_type VARCHAR(100),
    technology VARCHAR(100),
    
    -- Failure fields
    failure_description TEXT,
    error_message TEXT,
    solution_steps TEXT,
    
    -- Gate rejection fields
    gate_type VARCHAR(50),
    human_feedback TEXT,
    revision_approach TEXT,
    
    -- Gate approval fields
    approved_approach TEXT,
    
    -- Metadata
    success_verified BOOLEAN DEFAULT FALSE,
    embedded BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT NOW(),
    embedded_at TIMESTAMP,
    
    CHECK (
        (entry_type = 'failure_solution' AND failure_description IS NOT NULL) OR
        (entry_type = 'gate_rejection' AND gate_type IS NOT NULL) OR
        (entry_type = 'gate_approval' AND gate_type IS NOT NULL)
    )
);

CREATE INDEX idx_knowledge_staging_project ON knowledge_staging(project_id);
CREATE INDEX idx_knowledge_staging_embedded ON knowledge_staging(embedded);
```

### **Qdrant Collection**

```python
# Create collection
qdrant_client.create_collection(
    collection_name="project_knowledge",
    vectors_config=VectorParams(
        size=1536,  # text-embedding-3-small dimension
        distance=Distance.COSINE
    )
)

# Create payload indexes
qdrant_client.create_payload_index("project_knowledge", "entry_type", "keyword")
qdrant_client.create_payload_index("project_knowledge", "agent_type", "keyword")
qdrant_client.create_payload_index("project_knowledge", "task_type", "keyword")
qdrant_client.create_payload_index("project_knowledge", "technology", "keyword")
```

---

## Testing Strategy

### **Unit Tests**
- Knowledge capture (failures, rejections, approvals)
- Embedding generation and Qdrant storage
- Query filtering and pattern ranking
- Context formatting for agent consumption

### **Integration Tests**
- End-to-end knowledge flow (capture → stage → embed → query → retrieve)
- Orchestrator RAG integration
- Pruning system (1-year deletion)

### **End-to-End Tests**
- Cross-project learning (Project 1 failure → Project 2 receives solution)
- Human feedback loop (rejection → revision → future project benefits)
- Gold standard patterns (first-attempt approval → future project receives)

### **AI-Assisted Testing**
- Pattern relevance assessment (are retrieved patterns actually relevant?)
- Context clarity evaluation (does structured format prevent confusion?)
- Knowledge quality scoring (is stored knowledge valuable?)

---

## Implications

### **Enables**
- Cross-project learning and knowledge accumulation
- Reduced failure rates on similar tasks
- Faster problem resolution with historical patterns
- Human wisdom preservation and reuse
- Gold standard identification
- Continuous improvement over time

### **Requires**
- Qdrant vector database setup
- OpenAI embedding API integration
- Knowledge staging database tables
- Checkpoint trigger system
- Pruning automation (daily job)
- Orchestrator integration for queries

### **Trade-offs**
- **Embedding Costs**: OpenAI embedding API calls
- **Storage Costs**: Qdrant vector storage
- **Query Latency**: RAG queries add time to orchestrator decisions
- **Worth It**: Learning from past projects is invaluable, costs justified by quality improvement

---

## Dependencies

**Depends On**:
- Decision 67: Orchestrator LLM Integration (orchestrator-mediated RAG)
- Decision 57: Database selection (Qdrant for vectors, PostgreSQL for staging)

**Enables**:
- All agent learning capabilities
- Knowledge-driven problem solving
- Continuous quality improvement across projects

---

## Next Steps

1. ✅ Document this decision (COMPLETE)
2. ⏭️ Update development tracker
3. ⏭️ Move to Decision 69: Prompt Versioning

---

*Decision resolved: Nov 1, 2025*  
*Implementation priority: P0 - Required for learning system*
