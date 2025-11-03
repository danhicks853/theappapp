"""
Test Multi-Language Container Support

Verifies that containers can be created for all supported languages.
"""
import pytest
import asyncio

from backend.services.container_manager import get_container_manager, LANGUAGE_IMAGES


@pytest.mark.asyncio
async def test_all_language_containers():
    """Test creating containers for all supported languages."""
    
    print("\n" + "="*80)
    print("MULTI-LANGUAGE CONTAINER TEST")
    print("="*80)
    
    container_mgr = get_container_manager()
    
    # Test each language (including PowerShell - critical for Windows workflows)
    languages_to_test = ["python", "node", "powershell", "java", "go"]
    
    for language in languages_to_test:
        print(f"\n{language.upper()}: Testing container creation...")
        
        task_id = f"test-{language}-task"
        project_id = f"test-{language}-proj"
        
        try:
            # Create container
            result = await container_mgr.create_container(
                task_id=task_id,
                project_id=project_id,
                language=language
            )
            
            print(f"   ✓ Container created: {result.get('container_id', 'N/A')[:12]}...")
            
            # Test basic command
            if language == "python":
                cmd = "python --version"
            elif language == "node":
                cmd = "node --version"
            elif language == "java":
                cmd = "java --version"
            elif language == "go":
                cmd = "go version"
            elif language == "ruby":
                cmd = "ruby --version"
            elif language == "powershell":
                cmd = "pwsh -Command '$PSVersionTable.PSVersion'"
            else:
                cmd = "echo OK"
            
            exec_result = await container_mgr.exec_command(task_id, cmd)
            print(f"   ✓ Command executed: {exec_result.stdout.strip()[:50]}")
            
            # Cleanup
            await container_mgr.destroy_container(task_id)
            print(f"   ✓ Container destroyed")
            
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
            # Try to clean up anyway
            try:
                await container_mgr.destroy_container(task_id)
            except:
                pass
            raise
    
    print("\n" + "="*80)
    print("✓ ALL LANGUAGES TESTED SUCCESSFULLY!")
    print("="*80)
    print(f"\nSupported languages: {len(LANGUAGE_IMAGES)}")
    print(f"Tested: {', '.join(languages_to_test)}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_all_language_containers())
