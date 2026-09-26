from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str
    note: str | None = None
    priority: TaskPriority = TaskPriority.normal
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    project_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    note: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    project_id: str | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    note: str | None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    reminder_at: datetime | None
    project_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=10000)
    status: str = Field(default="active", min_length=1, max_length=32)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=10000)
    status: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one project field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Project name cannot be null")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Project status cannot be null")
        return self


class ProjectOut(BaseModel):
    id: str
    name: str
    summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteCreate(BaseModel):
    title: str
    body: str
    project_id: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    project_id: str | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one note field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Note title cannot be null")
        if "body" in self.model_fields_set and self.body is None:
            raise ValueError("Note body cannot be null")
        return self


class NoteOut(BaseModel):
    id: str
    title: str | None
    body: str | None
    project_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteLinkCreate(BaseModel):
    target_note_id: str


class HabitCreate(BaseModel):
    title: str = Field(max_length=500)
    recurrence_rule: str
    reminder_time: str | None = Field(default=None, max_length=16)


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    recurrence_rule: str | None = None
    reminder_time: str | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one habit field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Habit title cannot be null")
        if "recurrence_rule" in self.model_fields_set and self.recurrence_rule is None:
            raise ValueError("Habit recurrence_rule cannot be null")
        return self


class HabitOut(BaseModel):
    id: str
    title: str
    recurrence_rule: str
    reminder_time: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HabitCompletionOut(BaseModel):
    id: str
    habit_id: str
    completed_at: datetime

    model_config = {"from_attributes": True}


class ShoppingListCreate(BaseModel):
    name: str = Field(max_length=500)
    project_id: str | None = None


class ShoppingItemCreate(BaseModel):
    name: str = Field(max_length=500)
    category: str | None = Field(default=None, max_length=255)


class ShoppingItemUpdate(BaseModel):
    is_done: bool | None = None
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("is_done must be provided")
        if self.is_done is None:
            raise ValueError("is_done cannot be null")
        return self


class ShoppingItemOut(BaseModel):
    id: str
    list_id: str
    name: str
    category: str | None
    is_done: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ShoppingListOut(BaseModel):
    id: str
    name: str
    project_id: str | None
    created_at: datetime
    items: list[ShoppingItemOut]

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str = Field(max_length=500)
    template_type: str = Field(max_length=64)
    payload_json: str


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=500)
    template_type: str | None = Field(default=None, max_length=64)
    payload_json: str | None = None
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one template field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Template name cannot be null")
        if "template_type" in self.model_fields_set and self.template_type is None:
            raise ValueError("Template template_type cannot be null")
        if "payload_json" in self.model_fields_set and self.payload_json is None:
            raise ValueError("Template payload_json cannot be null")
        return self


class TemplateOut(BaseModel):
    id: str
    name: str
    template_type: str
    payload_json: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
