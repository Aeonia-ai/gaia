"""
Template Loader Service

Loads entity templates (items, NPCs, quests) from KB markdown files.
Templates are immutable blueprints defined in /experiences/{exp}/templates/.
Instances are runtime entities with mutable state.

This service handles:
- Loading template markdown from KB
- Parsing template properties
- Caching templates for performance
- Merging template + instance data
"""

import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Loads and caches entity templates from KB markdown files.

    Templates are defined in:
    /experiences/{experience}/templates/{entity_type}/{template_id}.md

    Where entity_type is: items, npcs, quests
    """

    def __init__(self, kb_root: Path):
        """
        Initialize template loader.

        Args:
            kb_root: Path to KB repository root
        """
        self.kb_root = kb_root
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def load_template(
        self,
        experience: str,
        entity_type: str,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load template definition from markdown file.

        Args:
            experience: Experience ID (e.g., "wylding-woods")
            entity_type: Entity type ("items", "npcs", "quests")
            template_id: Template ID (e.g., "dream_bottle", "louisa")

        Returns:
            Template properties dict, or None if not found
        """
        cache_key = f"{experience}/{entity_type}/{template_id}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load from file
        template_path = (
            self.kb_root /
            "experiences" /
            experience /
            "templates" /
            entity_type /
            f"{template_id}.md"
        )

        if not template_path.exists():
            logger.warning(
                f"Template not found: {template_path} "
                f"(experience={experience}, type={entity_type}, id={template_id})"
            )
            return None

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse template
            template = self._parse_template_markdown(content, template_id)

            # Cache it
            self._cache[cache_key] = template

            logger.debug(f"Loaded template: {cache_key}")
            return template

        except Exception as e:
            logger.error(f"Error loading template {cache_key}: {e}", exc_info=True)
            return None

    def _parse_template_markdown(
        self,
        content: str,
        template_id: str
    ) -> Dict[str, Any]:
        """
        Parse template markdown content into properties dict.

        Extracts:
        - Frontmatter (> **Field**: value)
        - Description section
        - Properties from Properties section

        Args:
            content: Markdown file content
            template_id: Template ID for fallback

        Returns:
            Template properties dict
        """
        template = {
            "template_id": template_id,
        }

        # Parse frontmatter (> **Field**: value)
        frontmatter_pattern = r'>\s*\*\*([^:]+)\*\*:\s*(.+)'
        for match in re.finditer(frontmatter_pattern, content):
            field_name = match.group(1).strip()
            field_value = match.group(2).strip()

            # Convert field names to snake_case
            key = field_name.lower().replace(' ', '_')
            template[key] = field_value

        # Parse Description section
        desc_match = re.search(
            r'##\s*Description\s*\n\n(.+?)(?=\n##|\Z)',
            content,
            re.DOTALL
        )
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove any leading/trailing whitespace and newlines
            description = ' '.join(description.split())
            template["description"] = description

        # Parse Properties section (bullet points)
        properties = {}
        props_match = re.search(
            r'##\s*Properties\s*\n\n(.+?)(?=\n##|\Z)',
            content,
            re.DOTALL
        )
        if props_match:
            props_content = props_match.group(1)
            # Parse bullet points
            prop_pattern = r'-\s*\*\*([^:]+)\*\*:\s*(.+)'
            for match in re.finditer(prop_pattern, props_content):
                prop_name = match.group(1).strip()
                prop_value = match.group(2).strip()
                key = prop_name.lower().replace(' ', '_')

                # Parse boolean values
                if prop_value.lower() in ('yes', 'true'):
                    prop_value = True
                elif prop_value.lower() in ('no', 'false'):
                    prop_value = False

                properties[key] = prop_value

            # Merge properties into template
            template.update(properties)

        # Ensure collectible field (default: False)
        if "collectible" not in template:
            template["collectible"] = False

        # Ensure visible field (default: True)
        if "visible" not in template:
            template["visible"] = True

        return template

    def merge_template_instance(
        self,
        template: Dict[str, Any],
        instance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge template properties with instance state.

        Instance fields override template fields.
        Instance state is preserved.

        Args:
            template: Template properties
            instance: Instance data with state

        Returns:
            Merged entity dict
        """
        merged = {
            **template,  # Template properties (immutable)
            **instance,  # Instance overrides
        }

        # Ensure we have both IDs
        if "template_id" not in merged and "template_id" in template:
            merged["template_id"] = template["template_id"]

        if "instance_id" not in merged and "instance_id" in instance:
            merged["instance_id"] = instance["instance_id"]

        return merged

    def clear_cache(self):
        """Clear template cache (useful for testing or hot-reload)."""
        self._cache.clear()
        logger.info("Template cache cleared")


# Singleton instance
_template_loader: Optional[TemplateLoader] = None


def get_template_loader(kb_root: Optional[Path] = None) -> TemplateLoader:
    """
    Get singleton template loader instance.

    Args:
        kb_root: KB repository root path (required on first call)

    Returns:
        TemplateLoader instance
    """
    global _template_loader

    if _template_loader is None:
        if kb_root is None:
            raise ValueError("kb_root required for first call to get_template_loader()")
        _template_loader = TemplateLoader(kb_root)

    return _template_loader
