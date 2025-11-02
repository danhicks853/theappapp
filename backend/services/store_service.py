"""
Store Service

Manages TheAppApp App Store - catalog of pre-built specialist templates.

Reference: TheAppApp App Store feature
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

STORE_DATA_PATH = Path(__file__).parent.parent / "data" / "store"


@dataclass
class SpecialistTemplate:
    """Specialist template from store."""
    template_id: str
    name: str
    display_name: str
    avatar_seed: str
    author: str
    current_version: str
    description: str
    bio: str
    interests: List[str]
    favorite_tool: str
    quote: str
    tags: List[str]


@dataclass
class TemplateVersion:
    """Specific version of a template."""
    version: str
    released: str
    system_prompt: str
    capabilities: List[str]
    web_search_enabled: bool
    web_search_config: Optional[Dict[str, Any]]
    tools_enabled: Dict[str, bool]
    changelog: str
    breaking_changes: bool


class StoreService:
    """
    Service for managing TheAppApp App Store.
    
    Features:
    - Browse specialist catalog
    - Get template details and versions
    - Install templates as specialists
    - Check for updates
    """
    
    def __init__(self, store_path: Path = STORE_DATA_PATH):
        """Initialize store service."""
        self.store_path = store_path
        self._catalog = None
        logger.info(f"Store service initialized (path: {store_path})")
    
    def _load_catalog(self) -> Dict[str, Any]:
        """Load store catalog from JSON."""
        if self._catalog is None:
            catalog_file = self.store_path / "catalog.json"
            if not catalog_file.exists():
                logger.error(f"Catalog not found: {catalog_file}")
                return {"specialists": []}
            
            with open(catalog_file, 'r') as f:
                self._catalog = json.load(f)
        
        return self._catalog
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[SpecialistTemplate]:
        """
        List all available specialist templates.
        
        Args:
            tags: Optional filter by tags
        
        Returns:
            List of specialist templates
        """
        catalog = self._load_catalog()
        templates = []
        
        for spec_data in catalog.get("specialists", []):
            # Filter by tags if provided
            if tags:
                spec_tags = set(spec_data.get("tags", []))
                if not any(tag in spec_tags for tag in tags):
                    continue
            
            template = SpecialistTemplate(
                template_id=spec_data["template_id"],
                name=spec_data["name"],
                display_name=spec_data["display_name"],
                avatar_seed=spec_data["avatar_seed"],
                author=spec_data["author"],
                current_version=spec_data["current_version"],
                description=spec_data["description"],
                bio=spec_data["bio"],
                interests=spec_data["interests"],
                favorite_tool=spec_data["favorite_tool"],
                quote=spec_data["quote"],
                tags=spec_data["tags"]
            )
            templates.append(template)
        
        logger.info(f"Listed {len(templates)} templates")
        return templates
    
    def get_template(self, template_id: str) -> Optional[SpecialistTemplate]:
        """Get a specific template by ID."""
        templates = self.list_templates()
        for template in templates:
            if template.template_id == template_id:
                return template
        return None
    
    def get_template_version(self, template_id: str, version: str) -> Optional[TemplateVersion]:
        """
        Get a specific version of a template.
        
        Args:
            template_id: Template ID
            version: Version string (e.g., "1.0.0")
        
        Returns:
            Template version details or None
        """
        version_file = self.store_path / template_id / f"v{version}.json"
        
        if not version_file.exists():
            logger.warning(f"Version file not found: {version_file}")
            return None
        
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
            
            return TemplateVersion(
                version=data["version"],
                released=data["released"],
                system_prompt=data["system_prompt"],
                capabilities=data["capabilities"],
                web_search_enabled=data["web_search_enabled"],
                web_search_config=data.get("web_search_config"),
                tools_enabled=data["tools_enabled"],
                changelog=data["changelog"],
                breaking_changes=data["breaking_changes"]
            )
        except Exception as e:
            logger.error(f"Error loading version {version} of {template_id}: {e}")
            return None
    
    def get_latest_version(self, template_id: str) -> Optional[str]:
        """Get the latest version number for a template."""
        template = self.get_template(template_id)
        return template.current_version if template else None
    
    def list_versions(self, template_id: str) -> List[str]:
        """List all available versions for a template."""
        template_dir = self.store_path / template_id
        if not template_dir.exists():
            return []
        
        versions = []
        for file in template_dir.glob("v*.json"):
            # Extract version from filename (v1.0.0.json -> 1.0.0)
            version = file.stem[1:]  # Remove 'v' prefix
            versions.append(version)
        
        # Sort versions (simple lexicographic for now)
        versions.sort(reverse=True)
        return versions
    
    def check_for_updates(self, template_id: str, current_version: str) -> Optional[str]:
        """
        Check if an update is available for a template.
        
        Args:
            template_id: Template ID
            current_version: Currently installed version
        
        Returns:
            Latest version if update available, None otherwise
        """
        latest = self.get_latest_version(template_id)
        
        if latest and latest != current_version:
            logger.info(f"Update available for {template_id}: {current_version} -> {latest}")
            return latest
        
        return None
    
    def install_template(
        self,
        template_id: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get installation data for a template.
        
        Args:
            template_id: Template to install
            version: Specific version (defaults to latest)
        
        Returns:
            Dict with all data needed to create specialist
        """
        # Get template metadata
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Get version (default to latest)
        if not version:
            version = template.current_version
        
        # Get version details
        version_data = self.get_template_version(template_id, version)
        if not version_data:
            raise ValueError(f"Version not found: {template_id} v{version}")
        
        # Combine data for installation
        installation_data = {
            "name": template.name,
            "display_name": template.display_name,
            "avatar": template.avatar_seed,
            "description": template.description,
            "system_prompt": version_data.system_prompt,
            "bio": template.bio,
            "interests": template.interests,
            "favorite_tool": template.favorite_tool,
            "quote": template.quote,
            "tags": template.tags,
            "version": version,
            "template_id": template_id,
            "installed_from_store": True,
            "web_search_enabled": version_data.web_search_enabled,
            "web_search_config": version_data.web_search_config,
            "tools_enabled": version_data.tools_enabled,
            "scope": "global"  # Store templates are global by default
        }
        
        logger.info(f"Prepared installation data for {template_id} v{version}")
        return installation_data
