"""
Paperless Metadata Helper

Helper class for managing document metadata and custom fields in Paperless-ngx.
This separates the business logic from the service layer.
"""

from typing import Dict, Any, Optional, List, Type
from services.paperless_service import PaperlessService


class PaperlessMetadataHelper:
    """
    Static helper class for managing Paperless document metadata.
    
    This class handles:
    - Creating/getting custom fields from Pydantic model schema
    - Mapping field names to field IDs
    - Preparing metadata for document upload
    
    All methods are static for easy usage without instantiation.
    """
    
    # Default metadata model class (can be overridden)
    DEFAULT_METADATA_MODEL = None  # Will be set when available
    
    @staticmethod
    def set_metadata_model(model_class: Type):
        """
        Set the metadata model class (Pydantic BaseModel).
        
        Args:
            model_class: Pydantic model class with Field definitions
        """
        PaperlessMetadataHelper.DEFAULT_METADATA_MODEL = model_class
    
    @staticmethod
    def extract_fields_from_model(model_class: Optional[Type] = None) -> Dict[str, str]:
        """
        Extract field names and types from a Pydantic model.
        
        Args:
            model_class: Pydantic model class. If None, uses DEFAULT_METADATA_MODEL.
        
        Returns:
            Dict mapping field_name -> data_type (string, date, integer, etc.)
        """
        if model_class is None:
            model_class = PaperlessMetadataHelper.DEFAULT_METADATA_MODEL
        
        if model_class is None:
            # Fallback to default schema if no model provided
            return PaperlessMetadataHelper._get_default_schema()
        
        fields_config = {}
        schema = model_class.model_json_schema()
        
        for field_name, field_props in schema.get('properties', {}).items():
            field_type = field_props.get('type', 'string')
            
            # Map JSON Schema types to Paperless custom field types
            if field_type == 'string':
                # Check if it's a date format
                if field_props.get('format') == 'date':
                    fields_config[field_name] = 'date'
                else:
                    fields_config[field_name] = 'string'
            elif field_type == 'integer':
                fields_config[field_name] = 'integer'
            elif field_type == 'number':
                fields_config[field_name] = 'float'
            elif field_type == 'boolean':
                fields_config[field_name] = 'boolean'
            else:
                fields_config[field_name] = 'string'
        
        return fields_config
    
    @staticmethod
    def _get_default_schema() -> Dict[str, str]:
        """
        Get default metadata schema as fallback.
        
        Returns:
            Dict mapping field_name -> data_type
        """
        return {
            "document_number": "string",
            "document_name": "string",
            "document_type": "string",
            "issue_date": "date",
            "effective_date": "date",
            "executing_unit": "string",
            "field": "string",
            "issuing_authority": "string",
            "security_level": "string",
            "status": "string"
        }
    
    @staticmethod
    def get_required_fields(model_class: Optional[Type] = None) -> List[str]:
        """
        Get required field names from a Pydantic model.
        
        Args:
            model_class: Pydantic model class. If None, uses DEFAULT_METADATA_MODEL.
        
        Returns:
            List of required field names
        """
        if model_class is None:
            model_class = PaperlessMetadataHelper.DEFAULT_METADATA_MODEL
        
        if model_class is None:
            # Fallback to default required fields
            return ["document_number", "document_name", "issue_date", "status"]
        
        schema = model_class.model_json_schema()
        return schema.get('required', [])
    
    @staticmethod
    async def initialize_fields(
        paperless_service: PaperlessService,
        model_class: Optional[Type] = None
    ) -> Dict[str, int]:
        """
        Initialize custom fields from Pydantic model schema.
        
        Args:
            paperless_service: PaperlessService instance
            model_class: Pydantic model class. If None, uses DEFAULT_METADATA_MODEL.
        
        Returns:
            Dict mapping field_name -> field_id
        """
        fields_config = PaperlessMetadataHelper.extract_fields_from_model(model_class)
        return await paperless_service.get_or_create_custom_fields(fields_config)
    
    @staticmethod
    def generate_metadata(
        filename: str, 
        model_class: Optional[Type] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate metadata from filename using model defaults.
        Includes ALL fields from the model (required + optional).
        Null values will be sent to Paperless as-is.
        
        Args:
            filename: Document filename
            model_class: Pydantic model class for defaults. If None, uses DEFAULT_METADATA_MODEL.
            extra_data: Optional extra metadata to merge
        
        Returns:
            Dict with ALL metadata fields (including None values)
        """
        if model_class is None:
            model_class = PaperlessMetadataHelper.DEFAULT_METADATA_MODEL
        
        # Clean filename to create title
        title = filename.replace(".pdf", "").replace("_", " ").replace("-", " ").title()
        
        if model_class is not None:
            # Get ALL field info from model schema
            schema = model_class.model_json_schema()
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            # Generate metadata for ALL fields
            metadata = {}
            for field_name, field_props in properties.items():
                if field_name in required:
                    # Required field - generate fake value
                    if field_name == 'document_number':
                        metadata[field_name] = f"TB-{len(filename)}"
                    elif field_name == 'document_name':
                        metadata[field_name] = title
                    elif field_name == 'issue_date':
                        # Use ISO format for dates (YYYY-MM-DD)
                        metadata[field_name] = "2026-03-20"
                    elif field_name == 'status':
                        metadata[field_name] = "Hiệu lực"
                    else:
                        metadata[field_name] = f"Default {field_name}"
                else:
                    # Optional field - use None (will be sent to Paperless as null)
                    metadata[field_name] = None
        else:
            # Fallback to hardcoded metadata with ALL fields
            metadata = {
                "document_number": f"TB-{len(filename)}",
                "document_name": title,
                "document_type": "Thông báo",
                "issue_date": "2026-03-20",
                "effective_date": None,
                "expiry_date": None,
                "executing_unit": None,
                "field": None,
                "issuing_authority": None,
                "security_level": None,
                "status": "Hiệu lực",
                "replaces_document": None,
                "replaced_by": None,
                "managing_unit": None,
                "receiving_units": None
            }
        
        # Merge with extra data if provided
        if extra_data:
            metadata.update(extra_data)
        
        return metadata
    
    @staticmethod
    def prepare_custom_fields_data(
        metadata: Dict[str, Any],
        field_ids: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """
        Prepare custom_fields array for Paperless API.
        
        Args:
            metadata: Dict mapping field_name -> value
            field_ids: Dict mapping field_name -> field_id
        
        Returns:
            List of {"field": field_id, "value": value} dicts
        """
        return [
            {"field": field_ids[key], "value": value}
            for key, value in metadata.items()
            if key in field_ids
        ]


# Export convenience functions
__all__ = ["PaperlessMetadataHelper"]
