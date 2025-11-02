#!/usr/bin/env python3
"""
Quick API Endpoint Test

Tests that all main API endpoints are accessible and working.

Run with: python -m backend.scripts.test_api_endpoints

Requires: FastAPI server running on http://localhost:8000
"""
import asyncio
import httpx
import json


BASE_URL = "http://localhost:8000"


async def test_endpoints():
    """Test all main API endpoints."""
    print("=" * 70)
    print("🧪 API ENDPOINT TESTS")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("1️⃣  Testing health endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            print(f"   ✅ Health: {response.json()}")
        except Exception as e:
            print(f"   ❌ Health failed: {e}")
        
        print()
        
        # Test 2: Root endpoint
        print("2️⃣  Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            assert response.status_code == 200
            print(f"   ✅ Root: {response.json()}")
        except Exception as e:
            print(f"   ❌ Root failed: {e}")
        
        print()
        
        # Test 3: List specialists (should be empty initially)
        print("3️⃣  Testing GET /api/v1/specialists...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/specialists")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                specialists = response.json()
                print(f"   ✅ Specialists endpoint working ({len(specialists)} specialists)")
            else:
                print(f"   ⚠️  Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Specialists failed: {e}")
        
        print()
        
        # Test 4: List projects
        print("4️⃣  Testing GET /api/v1/projects...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/projects")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                projects = response.json()
                print(f"   ✅ Projects endpoint working ({len(projects)} projects)")
            else:
                print(f"   ⚠️  Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Projects failed: {e}")
        
        print()
        
        # Test 5: Generate AI prompt (may fail without OpenAI key)
        print("5️⃣  Testing POST /api/v1/specialists/generate-prompt...")
        try:
            payload = {
                "name": "Test Expert",
                "description": "A test specialist",
                "role": "Testing expert",
                "capabilities": ["Unit testing", "Integration testing"]
            }
            response = await client.post(
                f"{BASE_URL}/api/v1/specialists/generate-prompt",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                prompt = result.get("system_prompt", "")
                print(f"   ✅ Prompt generated ({len(prompt)} chars)")
                print(f"   Preview: {prompt[:100]}...")
            else:
                print(f"   ⚠️  Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Generate prompt failed: {e}")
        
        print()
        print("=" * 70)
        print("✅ API ENDPOINT TESTS COMPLETE")
        print("=" * 70)
        print()
        print("📝 Notes:")
        print("   - Some endpoints may fail without database connection")
        print("   - Generate prompt requires OPENAI_API_KEY")
        print("   - This is a quick smoke test, not comprehensive")
        print()
        print("🚀 To start the server:")
        print("   uvicorn backend.api:app --reload")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(test_endpoints())
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
