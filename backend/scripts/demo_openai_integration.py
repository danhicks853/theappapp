#!/usr/bin/env python3
"""
Demo: OpenAI Integration Foundation

Demonstrates the complete OpenAI integration working end-to-end:
1. OpenAIAdapter making real API call
2. Token logging
3. Agent config loading

Run with: python -m backend.scripts.demo_openai_integration

REQUIRES: OPENAI_API_KEY environment variable
"""
import asyncio
import os
import sys


class SimpleTokenLogger:
    """Simple token logger for demo."""
    
    def log_tokens(self, model: str, prompt_tokens: int, completion_tokens: int, **kwargs):
        """Log token usage."""
        total = prompt_tokens + completion_tokens
        print(f"📊 TOKEN USAGE:")
        print(f"   Model: {model}")
        print(f"   Prompt tokens: {prompt_tokens}")
        print(f"   Completion tokens: {completion_tokens}")
        print(f"   Total tokens: {total}")
        print()


async def demo_openai_adapter():
    """Demo OpenAIAdapter with real API call."""
    from backend.services.openai_adapter import OpenAIAdapter
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("   Please set it with: $env:OPENAI_API_KEY='your-key-here'")
        return False
    
    print("=" * 60)
    print("🚀 OPENAI INTEGRATION DEMO")
    print("=" * 60)
    print()
    
    # Create adapter with token logger
    logger = SimpleTokenLogger()
    adapter = OpenAIAdapter(api_key=api_key, token_logger=logger)
    
    print("✅ OpenAIAdapter initialized")
    print(f"   API Key: {api_key[:15]}..." + "*" * 20)
    print()
    
    # Make a real chat completion call
    print("🤖 Calling OpenAI API...")
    print("   Prompt: 'Say hello and tell me you are working!'")
    print()
    
    try:
        response = await adapter.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant testing integration."},
                {"role": "user", "content": "Say hello and tell me you are working! Keep it brief."}
            ],
            temperature=0.7
        )
        
        print("✅ SUCCESS! Got response from OpenAI!")
        print()
        print("💬 RESPONSE:")
        print(f"   {response.choices[0].message.content}")
        print()
        
        # Token logger already printed stats
        
        print("=" * 60)
        print("🎉 INTEGRATION TEST PASSED!")
        print("=" * 60)
        print()
        print("✨ YOUR OPENAI INTEGRATION IS WORKING! ✨")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Integration test FAILED")
        return False


async def demo_agent_config():
    """Demo agent config system (without database)."""
    from backend.services.agent_model_config_service import AgentModelConfig
    
    print("=" * 60)
    print("⚙️  AGENT CONFIG DEMO (Defaults)")
    print("=" * 60)
    print()
    
    # Show default configs for a few agents
    agents = [
        AgentModelConfig('orchestrator', 'gpt-4o-mini', 0.3, 4096),
        AgentModelConfig('backend_dev', 'gpt-4o-mini', 0.7, 8192),
        AgentModelConfig('frontend_dev', 'gpt-4o-mini', 0.7, 8192),
    ]
    
    print("📋 Sample Agent Configurations:")
    print()
    for config in agents:
        print(f"   {config.agent_type:20} → {config.model:15} (temp={config.temperature}, max_tokens={config.max_tokens})")
    
    print()
    print("✅ Agent config system ready!")
    print("   (Full database integration requires DB setup)")
    print()


async def main():
    """Run the demo."""
    print()
    
    # Test OpenAI integration (requires API key)
    success = await demo_openai_adapter()
    
    if success:
        print()
        # Show agent config system
        await demo_agent_config()
        
        print("=" * 60)
        print("🎊 ALL SYSTEMS OPERATIONAL!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Set up PostgreSQL database")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Continue building Phase 1 features")
        print()
        print("🚀 YOU'RE READY TO BUILD AGENTS! 🚀")
        print()
        
        return 0
    else:
        print()
        print("Please fix the API key issue and try again.")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
