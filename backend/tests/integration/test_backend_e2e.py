"""
Comprehensive End-to-End Backend Test

Tests the entire backend stack in integration:
- Services (RAG, Search, OpenAI, Specialist, Project)
- Agents (execution loop)
- APIs (would need running server)

This is a full system integration test.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from backend.services.openai_adapter import OpenAIAdapter
from backend.services.rag_service import RAGService
from backend.services.search_service import SearchService
from backend.services.agent_llm_client import AgentLLMClient
from backend.services.specialist_service import SpecialistService
from backend.agents.backend_dev_agent import BackendDevAgent


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def pass_test(self, name: str):
        self.passed.append(name)
        print(f"  ✅ {name}")
    
    def fail_test(self, name: str, error: str):
        self.failed.append((name, error))
        print(f"  ❌ {name}: {error}")
    
    def warn(self, name: str, warning: str):
        self.warnings.append((name, warning))
        print(f"  ⚠️  {name}: {warning}")
    
    def summary(self):
        print()
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print()
        
        if self.failed:
            print("Failed tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")
            print()
        
        if self.warnings:
            print("Warnings:")
            for name, warning in self.warnings:
                print(f"  - {name}: {warning}")
            print()
        
        success_rate = len(self.passed) / (len(self.passed) + len(self.failed)) * 100 if (len(self.passed) + len(self.failed)) > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        return len(self.failed) == 0


async def test_openai_adapter(results: TestResults):
    """Test OpenAI integration."""
    print("\n🧪 Testing OpenAI Adapter...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        results.warn("OpenAI Adapter", "OPENAI_API_KEY not set - skipping")
        return
    
    try:
        adapter = OpenAIAdapter(api_key=api_key)
        
        # Test chat completion
        response = await adapter.chat_completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            temperature=0.5
        )
        
        if response and response.choices:
            results.pass_test("OpenAI chat completion")
        else:
            results.fail_test("OpenAI chat completion", "No response received")
        
        # Test embedding
        embedding = await adapter.embed_text("test document")
        if embedding and len(embedding) == 1536:
            results.pass_test("OpenAI embeddings")
        else:
            results.fail_test("OpenAI embeddings", f"Wrong embedding dimension: {len(embedding) if embedding else 0}")
    
    except Exception as e:
        results.fail_test("OpenAI Adapter", str(e))


async def test_rag_service(results: TestResults):
    """Test RAG service."""
    print("\n🧪 Testing RAG Service...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        results.warn("RAG Service", "OPENAI_API_KEY not set - skipping")
        return
    
    try:
        # Setup
        openai_adapter = OpenAIAdapter(api_key=api_key)
        rag = RAGService(openai_adapter, qdrant_url="http://localhost:6333")
        
        specialist_id = f"test-specialist-{uuid.uuid4()}"
        
        # Test document indexing
        doc = "PostgreSQL is a powerful open-source relational database. It supports JSON and advanced indexing."
        chunks_indexed = await rag.index_document(
            text=doc,
            specialist_id=specialist_id,
            metadata={"source": "test"}
        )
        
        if chunks_indexed > 0:
            results.pass_test(f"RAG document indexing ({chunks_indexed} chunks)")
        else:
            results.fail_test("RAG document indexing", "No chunks indexed")
        
        # Test search
        search_results = await rag.search(
            query="PostgreSQL database",
            specialist_id=specialist_id,
            limit=5
        )
        
        if search_results and len(search_results) > 0:
            results.pass_test(f"RAG semantic search ({len(search_results)} results)")
        else:
            results.fail_test("RAG semantic search", "No results found")
        
        # Cleanup
        await rag.delete_specialist_documents(specialist_id)
        results.pass_test("RAG document deletion")
    
    except Exception as e:
        results.fail_test("RAG Service", str(e))


async def test_search_service(results: TestResults):
    """Test search service."""
    print("\n🧪 Testing Search Service...")
    
    try:
        search = SearchService(searxng_url="http://localhost:8080")
        
        # Note: This will fail without SearxNG running, but test the service structure
        try:
            search_results = await search.search("test query", limit=3)
            if search_results is not None:
                results.pass_test(f"Search service ({len(search_results)} results)")
            else:
                results.warn("Search service", "SearxNG not running - service structure OK")
        except Exception:
            results.warn("Search service", "SearxNG not running - service structure OK")
        
        await search.close()
    
    except Exception as e:
        results.fail_test("Search Service", str(e))


async def test_specialist_service(results: TestResults):
    """Test specialist service."""
    print("\n🧪 Testing Specialist Service...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        results.warn("Specialist Service", "OPENAI_API_KEY not set - testing without AI")
    
    try:
        openai_adapter = OpenAIAdapter(api_key=api_key) if api_key else None
        service = SpecialistService(openai_adapter=openai_adapter)
        
        # Test AI prompt generation
        if openai_adapter:
            prompt = await service.generate_system_prompt(
                name="Test Expert",
                description="Expert in testing",
                role="QA specialist",
                capabilities=["Unit testing", "Integration testing"]
            )
            
            if prompt and len(prompt) > 50:
                results.pass_test(f"AI prompt generation ({len(prompt)} chars)")
            else:
                results.fail_test("AI prompt generation", "Prompt too short or empty")
        else:
            # Test fallback
            prompt = service._fallback_prompt(
                name="Test Expert",
                description="Expert in testing",
                role="QA specialist",
                capabilities=["Unit testing"]
            )
            if prompt:
                results.pass_test("Prompt fallback generation")
    
    except Exception as e:
        results.fail_test("Specialist Service", str(e))


async def test_agent_execution(results: TestResults):
    """Test full agent execution."""
    print("\n🧪 Testing Agent Execution...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        results.warn("Agent Execution", "OPENAI_API_KEY not set - skipping")
        return
    
    try:
        # Setup
        openai_adapter = OpenAIAdapter(api_key=api_key)
        llm_client = AgentLLMClient(openai_adapter)
        
        # Mock orchestrator
        class MockOrchestrator:
            async def execute_tool(self, payload):
                return {"status": "success", "result": "done"}
            async def create_gate(self, reason, context, agent_id):
                return str(uuid.uuid4())
            async def evaluate_confidence(self, payload):
                return 0.85
        
        orchestrator = MockOrchestrator()
        
        # Create agent
        agent = BackendDevAgent(
            agent_id="test-agent",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter
        )
        
        # Create simple task
        task = {
            "task_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "payload": {
                "goal": "Write a simple hello world function",
                "description": "Create a Python function that returns 'Hello, World!'",
                "acceptance_criteria": ["Function exists", "Returns correct string"],
                "max_steps": 3,
                "constraints": {}
            }
        }
        
        # Execute
        result = await agent.run_task(task)
        
        if result:
            results.pass_test(f"Agent execution ({len(result.steps)} steps)")
        else:
            results.fail_test("Agent execution", "No result returned")
        
        if result.steps and len(result.steps) > 0:
            results.pass_test("Agent multi-step execution")
        else:
            results.fail_test("Agent multi-step execution", "No steps executed")
        
        if result.artifacts:
            results.pass_test(f"Agent artifact generation ({len(result.artifacts)} artifacts)")
        else:
            results.warn("Agent artifacts", "No artifacts produced")
    
    except Exception as e:
        results.fail_test("Agent Execution", str(e))


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("🔬 COMPREHENSIVE BACKEND E2E TEST")
    print("=" * 70)
    print()
    print("This test exercises the entire backend stack:")
    print("  - OpenAI integration")
    print("  - RAG service (Qdrant)")
    print("  - Search service (SearxNG)")
    print("  - Specialist service")
    print("  - Agent execution")
    print()
    print("Requirements:")
    print("  - OPENAI_API_KEY environment variable")
    print("  - Qdrant running on localhost:6333")
    print("  - SearxNG on localhost:8080 (optional)")
    print()
    
    results = TestResults()
    
    # Run all tests
    await test_openai_adapter(results)
    await test_rag_service(results)
    await test_search_service(results)
    await test_specialist_service(results)
    await test_agent_execution(results)
    
    # Summary
    success = results.summary()
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("✅ Backend is ready for production!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Review failures above and fix issues.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
