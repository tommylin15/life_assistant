from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DriveWorkspaceCreate(BaseModel):
    google_folder_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=500)

    @field_validator("google_folder_id", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Drive workspace values cannot be blank")
        return normalized


class DriveWorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    is_enabled: bool | None = None
    is_default: bool | None = None
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one Drive workspace field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Drive workspace {field} cannot be null")
        if "name" in self.model_fields_set and self.name is not None:
            self.name = self.name.strip()
            if not self.name:
                raise ValueError("Drive workspace name cannot be blank")
        return self


class DriveWorkspaceOut(BaseModel):
    id: str
    google_folder_id: str
    name: str
    is_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriveDocumentRegister(BaseModel):
    google_file_ids: list[str] = Field(min_length=1, max_length=50)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("google_file_ids")
    @classmethod
    def normalize_file_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = raw.strip()
            if not value:
                raise ValueError("Google file ID cannot be blank")
            if len(value) > 255:
                raise ValueError("Google file ID is too long")
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        if not normalized:
            raise ValueError("At least one Google file ID is required")
        return normalized


class DriveDocumentOut(BaseModel):
    id: str
    google_file_id: str
    name: str
    mime_type: str
    web_view_link: str | None
    modified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriveDocumentRegisterOut(BaseModel):
    documents: list[DriveDocumentOut]
    returned: int


class DriveDocumentListOut(BaseModel):
    documents: list[DriveDocumentOut]
    returned: int


class DriveProjectLinksCreate(BaseModel):
    project_ids: list[str] = Field(min_length=1, max_length=100)

    @field_validator("project_ids")
    @classmethod
    def normalize_project_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = raw.strip()
            if not value:
                raise ValueError("Project ID cannot be blank")
            if len(value) > 36:
                raise ValueError("Project ID is too long")
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        if not normalized:
            raise ValueError("At least one Project ID is required")
        return normalized


class DriveProjectLinksOut(BaseModel):
    project_ids: list[str]
    returned: int


class DriveNoteImportRequest(BaseModel):
    title: str | None = Field(default=None, max_length=2000)
    project_id: str | None = Field(default=None, min_length=1, max_length=36)
    tags: list[str] = Field(default_factory=list, max_length=100)
    model_config = {"extra": "forbid"}

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("project_id")
    @classmethod
    def normalize_project_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project ID cannot be blank")
        return normalized

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = raw.strip()
            if not value:
                raise ValueError("Tag cannot be blank")
            if len(value) > 255:
                raise ValueError("Tag is too long")
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        return normalized


class PickerConfigOut(BaseModel):
    client_id: str
    developer_key: str
    app_id: str
    scope: str


class DriveEnrichmentSettingsOut(BaseModel):
    auto_tags_enabled: bool = True
    note_suggestions_enabled: bool = True
    allow_document_content: bool = False
    max_related_note_suggestions: int = Field(default=5, ge=1, le=20)

    model_config = {"from_attributes": True}


class DriveEnrichmentSettingsUpdate(BaseModel):
    auto_tags_enabled: bool | None = None
    note_suggestions_enabled: bool | None = None
    allow_document_content: bool | None = None
    max_related_note_suggestions: int | None = Field(default=None, ge=1, le=20)
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one enrichment setting must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Enrichment setting {field} cannot be null")
        return self


class DriveEnrichmentRunRequest(BaseModel):
    force: bool = False


class DriveNoteSuggestionDecision(BaseModel):
    decision: Literal["accepted", "rejected"]


class DriveNoteSuggestionOut(BaseModel):
    id: str
    note_id: str
    confidence: float
    reason: str
    decision: Literal["pending", "accepted", "rejected"]
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DriveEnrichmentRunOut(BaseModel):
    id: str
    drive_document_id: str
    content_fingerprint: str
    provider: str | None
    model: str | None
    status: Literal["succeeded", "partial", "failed", "skipped"]
    suggested_tags: list[str]
    note_suggestions: list[DriveNoteSuggestionOut]
    error_code: str | None
    cache_hit: bool = False
    created_at: datetime
