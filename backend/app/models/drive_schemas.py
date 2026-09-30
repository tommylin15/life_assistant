from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class DriveWorkspaceCreate(BaseModel):
    google_folder_id: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, max_length=500)


class DriveWorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    is_enabled: bool | None = None
    is_default: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one Drive workspace field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Drive workspace {field} cannot be null")
        return self


class DriveWorkspaceOut(BaseModel):
    id: str
    google_folder_id: str
    name: str
    web_view_link: str | None
    is_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriveDocumentOut(BaseModel):
    id: str
    google_file_id: str
    name: str
    mime_type: str
    web_view_link: str | None
    provider_modified_at: datetime | None
    last_metadata_refresh_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriveDocumentsRegister(BaseModel):
    google_file_ids: list[str] = Field(min_length=1, max_length=100)
    workspace_id: str | None = None

    @field_validator("google_file_ids")
    @classmethod
    def normalize_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = raw.strip()
            if not value:
                raise ValueError("Google file id cannot be empty")
            if len(value) > 255:
                raise ValueError("Google file id is too long")
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        if not normalized:
            raise ValueError("At least one Google file id is required")
        return normalized


class DriveAiSettingsOut(BaseModel):
    auto_tags: bool = True
    suggest_related_notes: bool = True
    allow_content_analysis: bool = False
    max_related_notes: int = Field(default=5, ge=1, le=10)

    model_config = {"from_attributes": True}


class DriveAiSettingsUpdate(BaseModel):
    auto_tags: bool | None = None
    suggest_related_notes: bool | None = None
    allow_content_analysis: bool | None = None
    max_related_notes: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def require_non_null_changes(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Drive AI setting {field} cannot be null")
        return self


class DriveNoteLinkSuggestionOut(BaseModel):
    id: str
    drive_document_id: str
    note_id: str
    confidence: float
    reason: str
    decision: str
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PickerConfigOut(BaseModel):
    client_id: str
    developer_key: str
    app_id: str
    scope: str
