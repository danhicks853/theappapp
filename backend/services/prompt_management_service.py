"""
Prompt Management Service

Manages prompt versioning: create, promote, and patch.
Implements semantic versioning (major.minor.patch) with fix-forward only.

Reference: Section 1.2.4 - Prompt Versioning System
"""
import logging
import re
from typing import Optional, List, Dict, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PromptManagementService:
    """
    Service for managing prompt versions.
    
    Features:
    - Create new prompt versions (semantic versioning)
    - Promote version to active
    - Create patch versions (fix-forward only, no rollback)
    - Independent versioning per agent type
    - Validation and constraints
    
    Example:
        service = PromptManagementService(engine)
        await service.create_version(
            agent_type="backend_dev",
            version="1.1.0",
            prompt_text="New improved prompt...",
            created_by="user-1",
            notes="Added error handling guidelines"
        )
        await service.promote_to_active("backend_dev", "1.1.0")
    """
    
    def __init__(self, engine: Engine):
        """Initialize prompt management service."""
        self.engine = engine
        logger.info("PromptManagementService initialized")
    
    async def create_version(
        self,
        agent_type: str,
        version: str,
        prompt_text: str,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Create a new prompt version.
        
        Args:
            agent_type: Agent type identifier
            version: Semantic version (major.minor.patch)
            prompt_text: Prompt content
            created_by: User who created the version
            notes: Optional notes about this version
        
        Returns:
            True if created successfully
        
        Raises:
            ValueError: If version format invalid or version already exists
        """
        # Validate version format
        if not self._validate_version(version):
            raise ValueError(f"Invalid version format: {version}. Must be major.minor.patch (e.g., 1.0.0)")
        
        logger.info(f"Creating prompt version {version} for {agent_type}")
        
        try:
            query = text("""
                INSERT INTO prompts (agent_type, version, prompt_text, is_active, created_by, notes, created_at)
                VALUES (:agent_type, :version, :prompt_text, false, :created_by, :notes, NOW())
            """)
            
            with self.engine.connect() as conn:
                conn.execute(query, {
                    "agent_type": agent_type,
                    "version": version,
                    "prompt_text": prompt_text,
                    "created_by": created_by,
                    "notes": notes
                })
                conn.commit()
                
            logger.info(f"Created version {version} for {agent_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            if "unique constraint" in str(e).lower():
                raise ValueError(f"Version {version} already exists for {agent_type}")
            raise
    
    async def promote_to_active(
        self,
        agent_type: str,
        version: str
    ) -> bool:
        """
        Promote a version to active (only one active per agent type).
        
        Args:
            agent_type: Agent type identifier
            version: Version to promote
        
        Returns:
            True if promoted successfully
        
        Raises:
            RuntimeError: If version not found
        """
        logger.info(f"Promoting {agent_type} version {version} to active")
        
        with self.engine.connect() as conn:
            # First, verify version exists
            check_query = text("""
                SELECT id FROM prompts
                WHERE agent_type = :agent_type AND version = :version
            """)
            result = conn.execute(check_query, {"agent_type": agent_type, "version": version})
            if not result.fetchone():
                raise RuntimeError(f"Version {version} not found for {agent_type}")
            
            # Deactivate all versions for this agent
            deactivate_query = text("""
                UPDATE prompts
                SET is_active = false
                WHERE agent_type = :agent_type
            """)
            conn.execute(deactivate_query, {"agent_type": agent_type})
            
            # Activate the specified version
            activate_query = text("""
                UPDATE prompts
                SET is_active = true
                WHERE agent_type = :agent_type AND version = :version
            """)
            conn.execute(activate_query, {"agent_type": agent_type, "version": version})
            conn.commit()
            
        logger.info(f"Promoted {agent_type} version {version} to active")
        return True
    
    async def create_patch(
        self,
        agent_type: str,
        prompt_text: str,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Create a patch version (increments patch number).
        Fix-forward only - no rollback.
        
        Args:
            agent_type: Agent type identifier
            prompt_text: New prompt content
            created_by: User who created the patch
            notes: Optional notes about this patch
        
        Returns:
            New version string (e.g., "1.0.1")
        
        Raises:
            RuntimeError: If no active version found
        """
        logger.info(f"Creating patch for {agent_type}")
        
        with self.engine.connect() as conn:
            # Get current active version
            query = text("""
                SELECT version
                FROM prompts
                WHERE agent_type = :agent_type AND is_active = true
            """)
            result = conn.execute(query, {"agent_type": agent_type})
            row = result.fetchone()
            
            if not row:
                raise RuntimeError(f"No active version found for {agent_type}")
            
            current_version = row[0]
            new_version = self._increment_patch(current_version)
            
        # Create new version
        await self.create_version(
            agent_type=agent_type,
            version=new_version,
            prompt_text=prompt_text,
            created_by=created_by,
            notes=notes or f"Patch from {current_version}"
        )
        
        # Promote to active
        await self.promote_to_active(agent_type, new_version)
        
        logger.info(f"Created and activated patch version {new_version} for {agent_type}")
        return new_version
    
    async def get_versions(self, agent_type: str) -> List[Dict[str, Any]]:
        """
        Get all versions for an agent type.
        
        Args:
            agent_type: Agent type identifier
        
        Returns:
            List of version dictionaries
        """
        logger.debug(f"Fetching versions for {agent_type}")
        
        query = text("""
            SELECT version, is_active, created_at, created_by, notes
            FROM prompts
            WHERE agent_type = :agent_type
            ORDER BY created_at DESC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"agent_type": agent_type})
            rows = result.fetchall()
            
            versions = [
                {
                    "version": row[0],
                    "is_active": row[1],
                    "created_at": row[2].isoformat() if row[2] else None,
                    "created_by": row[3],
                    "notes": row[4]
                }
                for row in rows
            ]
            
        logger.info(f"Found {len(versions)} versions for {agent_type}")
        return versions
    
    async def get_prompt_content(self, agent_type: str, version: str) -> Optional[str]:
        """
        Get prompt content for specific version.
        
        Args:
            agent_type: Agent type identifier
            version: Version to retrieve
        
        Returns:
            Prompt text or None if not found
        """
        query = text("""
            SELECT prompt_text
            FROM prompts
            WHERE agent_type = :agent_type AND version = :version
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"agent_type": agent_type, "version": version})
            row = result.fetchone()
            
            return row[0] if row else None
    
    def _validate_version(self, version: str) -> bool:
        """Validate semantic version format (major.minor.patch)."""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _increment_patch(self, version: str) -> str:
        """Increment patch version (e.g., 1.0.0 → 1.0.1)."""
        parts = version.split('.')
        parts[2] = str(int(parts[2]) + 1)
        return '.'.join(parts)
