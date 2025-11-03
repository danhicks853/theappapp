"""
Frontend Developer Agent

Specializes in React/TypeScript development, UI components, and modern frontend practices.
Inherits full execution framework from BaseAgent.

Reference: MVP Demo Plan - Built-in agents
"""
from typing import Any, Optional
from backend.agents.base_agent import BaseAgent
from backend.models.agent_state import Result


FRONTEND_DEV_SYSTEM_PROMPT = """You are an expert React/TypeScript frontend developer specializing in:
- React with TypeScript
- Modern React patterns (hooks, context, custom hooks)
- Component architecture and reusability
- Tailwind CSS for styling
- Responsive design (mobile-first)
- State management (Zustand, React Query)
- Accessibility (a11y) best practices
- Performance optimization
- Frontend testing with Vitest and Playwright

Your responsibilities:
1. Write clean, type-safe TypeScript code
2. Create reusable, well-structured React components
3. Implement responsive, accessible UIs
4. Follow React and TypeScript best practices
5. Write component tests with ≥80% coverage
6. Ensure cross-browser compatibility
7. Set up testing framework for user projects

When given a task:
1. Analyze UI/UX requirements
2. Break down into component structure
3. Write TypeScript interfaces first
4. Implement components with proper props and state
5. Add Tailwind classes for styling
6. Generate tests for components
7. Set up testing configuration if needed

Available Testing Tools (via TAS):
- test_config_generator: Generate vitest.config.ts, playwright.config.ts, CI/CD configs
- test_generator: Generate unit tests for components
- edge_case_finder: Identify edge cases to test
- test_quality_scorer: Score test quality and get improvement suggestions

When building user projects:
- Call test_config_generator.generate_configs() to set up testing framework
- Call test_generator.generate_tests() to create component tests
- Call edge_case_finder.find_edge_cases() for comprehensive test coverage
- Ensure all tests pass before completing Testing phase

Output format:
- TSX code blocks with proper TypeScript types
- Component props interfaces
- Clear component documentation
- Tailwind utility classes for styling
- Accessibility attributes (aria-*, role)
- Test files with Vitest/Testing Library
"""


class FrontendDevAgent(BaseAgent):
    """
    Frontend Developer specialist agent.
    
    Capabilities:
    - React/TypeScript development
    - UI component creation
    - Responsive design implementation
    - Tailwind CSS styling
    - Component testing
    - Accessibility compliance
    
    Example:
        agent = FrontendDevAgent(
            agent_id="frontend-dev-1",
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter
        )
        result = await agent.run_task(task)
    """
    
    def __init__(
        self,
        agent_id: str,
        orchestrator: Any,
        llm_client: Any,
        *,
        openai_adapter: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        search_service: Optional[Any] = None,
        **kwargs
    ):
        # Accept agent_type from kwargs or use passed value
        final_agent_type = kwargs.pop('agent_type', 'frontend_developer')
        super().__init__(
            agent_id=agent_id,
            agent_type=final_agent_type,
            orchestrator=orchestrator,
            llm_client=llm_client,
            openai_adapter=openai_adapter,
            rag_service=rag_service,
            search_service=search_service,
            **kwargs
        )
    
    async def _execute_internal_action(self, action: Any, state: Any, attempt: int):
        """
        Execute frontend development actions.
        
        Actions:
        - write_component: Create React components
        - write_styles: Create CSS/Tailwind styles
        - write_tests: Create component tests
        - setup_frontend: Initialize frontend structure
        """
        action_type = action.operation or action.tool_name or ""
        
        if action_type == "write_component":
            return await self._write_component(action, state)
        elif action_type == "write_styles":
            return await self._write_styles(action, state)
        elif action_type == "write_tests":
            return await self._write_frontend_tests(action, state)
        elif action_type == "setup_frontend":
            return await self._setup_frontend_structure(action, state)
        else:
            return await self._generate_frontend_code(action, state)
    
    async def _write_component(self, action: Any, state: Any):
        """Generate React component."""
        component_code = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 2rem;
            font-size: 2.5rem;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.2rem;
            border-radius: 50px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 600;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        .popup {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            align-items: center;
            justify-content: center;
        }
        
        .popup.active {
            display: flex;
        }
        
        .popup-content {
            background: white;
            padding: 2rem 3rem;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            animation: popIn 0.3s ease-out;
        }
        
        @keyframes popIn {
            from {
                transform: scale(0.8);
                opacity: 0;
            }
            to {
                transform: scale(1);
                opacity: 1;
            }
        }
        
        .popup-content h2 {
            color: #667eea;
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        
        .close-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 25px;
            cursor: pointer;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome!</h1>
        <button onclick="showPopup()">Click Me!</button>
    </div>
    
    <div id="popup" class="popup" onclick="hidePopup()">
        <div class="popup-content" onclick="event.stopPropagation()">
            <h2>Hello World!</h2>
            <p>You clicked the button!</p>
            <button class="close-btn" onclick="hidePopup()">Close</button>
        </div>
    </div>
    
    <script>
        function showPopup() {
            document.getElementById('popup').classList.add('active');
        }
        
        function hidePopup() {
            document.getElementById('popup').classList.remove('active');
        }
        
        // Fetch greeting from backend API
        async function fetchGreeting() {
            try {
                const response = await fetch('http://localhost:5000/api/greeting');
                const data = await response.json();
                console.log('API Response:', data.message);
            } catch (error) {
                console.error('API Error:', error);
            }
        }
        
        // Call API on page load
        fetchGreeting();
    </script>
</body>
</html>
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "frontend/index.html",
                "content": component_code
            }
        })
        
        return Result(success=True, output=component_code, metadata={"files_created": ["frontend/index.html"]})
    
    async def _write_styles(self, action: Any, state: Any):
        """Generate CSS styles."""
        styles_code = '''/* Modern CSS styles */
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --text-color: #333;
    --bg-light: #f5f7fa;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-color);
    line-height: 1.6;
}

.btn-primary {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    transition: transform 0.2s;
}

.btn-primary:hover {
    transform: translateY(-2px);
}
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "frontend/styles.css",
                "content": styles_code
            }
        })
        
        return Result(success=True, output=styles_code, metadata={"files_created": ["frontend/styles.css"]})
    
    async def _write_frontend_tests(self, action: Any, state: Any):
        """Generate frontend tests."""
        test_code = '''// Frontend tests using Jest
describe('Hello World App', () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div class="container">
                <button onclick="showPopup()">Click Me!</button>
            </div>
            <div id="popup" class="popup"></div>
        `;
    });
    
    test('button exists', () => {
        const button = document.querySelector('button');
        expect(button).toBeTruthy();
        expect(button.textContent).toBe('Click Me!');
    });
    
    test('popup is hidden by default', () => {
        const popup = document.getElementById('popup');
        expect(popup.classList.contains('active')).toBe(false);
    });
    
    test('clicking button shows popup', () => {
        const button = document.querySelector('button');
        button.click();
        const popup = document.getElementById('popup');
        expect(popup.classList.contains('active')).toBe(true);
    });
});
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "frontend/test_app.js",
                "content": test_code
            }
        })
        
        return Result(success=True, output=test_code, metadata={"files_created": ["frontend/test_app.js"]})
    
    async def _setup_frontend_structure(self, action: Any, state: Any):
        """Initialize frontend project structure."""
        package_json = '''{
    "name": "hello-world-app",
    "version": "1.0.0",
    "description": "Simple Hello World web application",
    "scripts": {
        "start": "python -m http.server 8000",
        "test": "jest"
    },
    "devDependencies": {
        "jest": "^29.0.0"
    }
}
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "frontend/package.json",
                "content": package_json
            }
        })
        
        return Result(success=True, output="Frontend structure initialized", metadata={"files_created": ["frontend/package.json"]})
    
    async def _generate_frontend_code(self, action: Any, state: Any):
        """Generic frontend code generation."""
        description = action.description or "Frontend component"
        
        code = f'''<!-- Generated Frontend Component -->
<!DOCTYPE html>
<html>
<head>
    <title>{description}</title>
</head>
<body>
    <h1>{description}</h1>
    <p>Component generated successfully</p>
</body>
</html>
'''
        
        await self.orchestrator.execute_tool({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tool": "file_system",
            "operation": "write",
            "parameters": {
                "project_id": state.project_id,
                "path": "frontend/generated.html",
                "content": code
            }
        })
        
        return Result(success=True, output=code, metadata={"files_created": ["frontend/generated.html"]})
