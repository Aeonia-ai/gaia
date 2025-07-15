from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid

from .asset import AssetCategory, AssetQuality, LicenseType, StorageInfo, AssetData


class AssetSourceType(str, Enum):
    OPEN_SOURCE = "open_source"
    COMMUNITY = "community"
    GENERATED = "generated"
    COMMERCIAL = "commercial"


class ExternalAssetSource(BaseModel):
    source_name: str = Field(..., description="Name of the external source")
    source_type: AssetSourceType
    api_endpoint: Optional[str] = None
    is_active: bool = Field(default=True)
    rate_limit_per_minute: Optional[int] = Field(None, description="API rate limit")
    requires_attribution: bool = Field(default=False)
    cost_per_request: float = Field(default=0.0, description="Cost per API request")


class DatabaseAsset(BaseModel):
    id: str
    source_id: int
    external_id: Optional[str] = None
    category: AssetCategory
    title: str
    description: str
    style_tags: List[str] = Field(default_factory=list)
    file_url: str
    storage_info: StorageInfo
    file_size_mb: float
    file_format: str
    preview_image_url: str
    quality_score: float = Field(ge=0, le=1)
    download_count: int = Field(default=0)
    license_type: LicenseType
    attribution_required: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    created_at: datetime
    updated_at: datetime


class ExternalAsset(BaseModel):
    external_id: str
    source_name: str = Field(..., description="Source like poly_haven, freesound")
    title: str
    description: str
    category: AssetCategory
    style_tags: List[str] = Field(default_factory=list)
    download_url: str
    preview_image_url: Optional[str] = None
    file_format: str
    file_size_mb: Optional[float] = None
    quality_score: float = Field(default=0.5, ge=0, le=1)
    license_type: LicenseType
    attribution_required: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cost_to_access: float = Field(default=0.0, description="Cost to access this asset")


class GeneratedAsset(BaseModel):
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = Field(..., description="Generation prompt used")
    category: AssetCategory
    style: str
    title: str
    description: str
    asset_data: AssetData
    storage_info: StorageInfo
    generation_cost: float = Field(ge=0, description="Cost of generation")
    generation_time_ms: int = Field(ge=0, description="Time taken to generate")
    generation_service: str = Field(..., description="Service used: meshy, midjourney, etc.")
    quality_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModifiedAsset(BaseModel):
    modification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    base_asset_id: str = Field(..., description="Original asset ID")
    modifications: List[str] = Field(..., description="List of modifications applied")
    modified_asset_data: AssetData
    storage_info: StorageInfo
    modification_cost: float = Field(ge=0, description="Cost of modifications")
    modification_time_ms: int = Field(ge=0, description="Time taken to modify")
    modification_service: str = Field(..., description="Service used for modification")
    quality_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)




class OptimizationStrategy(BaseModel):
    strategy_type: str = Field(..., description="database, hybrid, or generation")
    estimated_cost: float = Field(ge=0)
    estimated_time_ms: int = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1, description="Confidence in strategy success")
    fallback_strategy: Optional[str] = None
    reasoning: str = Field(..., description="Why this strategy was chosen")