from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class AssetCategory(str, Enum):
    ENVIRONMENT = "environment"
    CHARACTER = "character"
    PROP = "prop"
    AUDIO = "audio"
    TEXTURE = "texture"
    ANIMATION = "animation"
    IMAGE = "image"


class AssetQuality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class AssetSource(str, Enum):
    DATABASE = "database"
    HYBRID = "hybrid"
    GENERATED = "generated"
    EXTERNAL = "external"


class LicenseType(str, Enum):
    CREATIVE_COMMONS = "creative_commons"
    PUBLIC_DOMAIN = "public_domain"
    CUSTOM = "custom"
    COMMERCIAL = "commercial"
    PROPRIETARY = "proprietary"


class StorageType(str, Enum):
    SUPABASE = "supabase"
    EXTERNAL = "external"
    GENERATED = "generated"


class AssetRequirements(BaseModel):
    platform: str = Field(..., description="Target platform: mobile_vr, desktop_vr, ar")
    quality: AssetQuality = Field(default=AssetQuality.MEDIUM, description="Required quality level")
    polygon_count_max: Optional[int] = Field(None, description="Maximum polygon count for 3D assets")
    file_size_max_mb: Optional[int] = Field(None, description="Maximum file size in MB")
    format: Optional[str] = Field(None, description="Preferred file format")


class AssetPreferences(BaseModel):
    allow_database: bool = Field(default=True, description="Allow database search")
    allow_modifications: bool = Field(default=True, description="Allow asset modifications")
    allow_generation: bool = Field(default=True, description="Allow AI generation")
    max_cost: float = Field(default=0.50, description="Maximum cost in USD")
    max_wait_time_ms: int = Field(default=5000, description="Maximum wait time in milliseconds")


class AssetRequest(BaseModel):
    category: AssetCategory = Field(..., description="Asset category")
    style: str = Field(..., description="Asset style: sci_fi, medieval, cartoon, etc.")
    description: str = Field(..., description="Detailed description of the asset")
    requirements: Optional[AssetRequirements] = None
    preferences: Optional[AssetPreferences] = None
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class StorageInfo(BaseModel):
    storage_type: StorageType
    bucket_name: Optional[str] = None
    file_path: Optional[str] = None
    external_source: Optional[str] = None


class AssetData(BaseModel):
    download_url: str = Field(..., description="URL to download the asset")
    preview_image_url: str = Field(..., description="URL for preview image")
    file_format: str = Field(..., description="File format: gltf, fbx, wav, png, etc.")
    file_size_mb: float = Field(..., description="File size in megabytes")
    quality_score: float = Field(..., ge=0, le=1, description="Quality score 0-1")
    license_type: LicenseType
    attribution_required: bool = Field(default=False)


class CostBreakdown(BaseModel):
    search_cost: float = Field(default=0.0, description="Cost of searching databases")
    modification_cost: float = Field(default=0.0, description="Cost of AI modifications")
    generation_cost: float = Field(default=0.0, description="Cost of AI generation")
    storage_cost: float = Field(default=0.0, description="Cost of storage")
    total_cost: float = Field(..., description="Total cost")


class AssetMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: AssetCategory
    title: str
    description: str
    style_tags: List[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0, le=1)
    download_count: int = Field(default=0)
    license_type: LicenseType
    attribution_required: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetResponse(BaseModel):
    asset_id: str
    source: AssetSource
    cost: float = Field(ge=0, description="Total cost in USD")
    response_time_ms: int = Field(ge=0, description="Response time in milliseconds")
    asset_data: AssetData
    storage_info: StorageInfo
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cost_breakdown: Optional[CostBreakdown] = None


class AssetUploadResponse(BaseModel):
    asset_id: str
    upload_url: str = Field(..., description="URL where the asset was uploaded")
    preview_url: str = Field(..., description="URL for the preview image")
    status: str = Field(default="uploaded", description="Upload status")
    message: str = Field(default="Asset uploaded successfully")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AssetSearchResult(BaseModel):
    assets: List[AssetMetadata]
    total_count: int
    query_time_ms: int
    search_strategy: str = Field(description="Strategy used: database, external, hybrid")


class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation")
    style: str = Field(default="realistic", description="Style: realistic, cartoon, artistic, etc.")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio: 1:1, 16:9, 9:16, etc.")
    quality: AssetQuality = Field(default=AssetQuality.MEDIUM)
    seed: Optional[int] = Field(None, description="Random seed for reproducible generation")
    negative_prompt: Optional[str] = Field(None, description="What to avoid in generation")


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationResponse(BaseModel):
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: GenerationStatus
    image_url: Optional[str] = None
    preview_url: Optional[str] = None
    progress_percentage: float = Field(default=0.0, ge=0, le=100)
    estimated_completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    generation_cost: float = Field(default=0.0)
    generation_time_ms: Optional[int] = None


# Database and Generation Asset Classes for Service Layer
class DatabaseAsset(BaseModel):
    id: str
    category: str
    title: str
    description: str
    style_tags: List[str] = Field(default_factory=list)
    quality_score: float
    download_count: int = Field(default=0)
    license_type: LicenseType
    attribution_required: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    asset_data: AssetData


class ExternalAsset(BaseModel):
    source_name: str
    external_id: str
    title: str
    description: str
    category: str
    quality_score: float
    license_type: LicenseType
    attribution_required: bool = Field(default=False)
    asset_data: AssetData


class GeneratedAsset(BaseModel):
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generation_service: str
    generation_cost: float
    generation_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    asset_data: AssetData


class ModifiedAsset(BaseModel):
    modification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    base_asset_id: str
    modification_service: str
    modification_cost: float
    modification_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    asset_data: AssetData