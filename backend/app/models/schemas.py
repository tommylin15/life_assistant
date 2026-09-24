from datetime import datetime

from pydantic import BaseModel

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
