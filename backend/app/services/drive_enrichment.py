from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drive import (
    DriveDocument,
    DriveDocumentEnrichmentRun,
    DriveEnrichmentSettings,
    DriveNoteLinkSuggestion,
    NoteDriveDocument,
    ProjectDriveDocument,
)
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.models.project import Project
from app.services import drive_documents
from app.services.ai_enrichment_provider import (
    AIEnrichmentProvider,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    compute_enrichment_fingerprint,
    execute_provider_enrichment,
    get_ai_enrichment_provider,
)

_MAX_CANDIDATES = 20
_MAX_NOTE_TITLE = 300
_MAX_NOTE_SNIPPET = 500
_KEYWORD_LIMIT = 6


async def get_enrichment_settings(
    db: AsyncSession,
    user_sub: str,
) -> DriveEnrichmentSettings:
    settings = await db.get(DriveEnrichmentSettings, user_sub)
    if settings is not None:
        return settings
    return DriveEnrichmentSettings(
        user_sub=user_sub,
        auto_tags_enabled=True,
        note_suggestions_enabled=True,
        allow_document_content=False,
        max_related_note_suggestions=5,
    )


async def update_enrichment_settings(
    db: AsyncSession,
    user_sub: str,
    changes: dict[str, object],
) -> DriveEnrichmentSettings:
    settings = await db.get(DriveEnrichmentSettings, user_sub)
    if settings is None:
        settings = DriveEnrichmentSettings(
            user_sub=user_sub,
            auto_tags_enabled=True,
            note_suggestions_enabled=True,
            allow_document_content=False,
            max_related_note_suggestions=5,
        )
        db.add(settings)
    for field, value in changes.items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return settings


async def _document_projects(
    db: AsyncSession,
    document_id: str,
) -> tuple[list[str], tuple[str, ...]]:
    project_ids = list(
        (
            await db.execute(
                select(ProjectDriveDocument.project_id).where(
                    ProjectDriveDocument.drive_document_id == document_id
                )
            )
        ).scalars().all()
    )
    if not project_ids:
        return [], ()
    names = list(
        (
            await db.execute(
                select(Project.name)
                .where(Project.id.in_(project_ids))
                .order_by(func.lower(Project.name))
            )
        ).scalars().all()
    )
    return project_ids, tuple(str(name)[:500] for name in names)


async def _document_tags(
    db: AsyncSession,
    document_id: str,
) -> tuple[list[str], tuple[str, ...]]:
    rows = (
        await db.execute(
            select(Tag.id, Tag.name)
            .join(EntityTag, EntityTag.tag_id == Tag.id)
            .where(
                EntityTag.entity_type == "drive_document",
                EntityTag.entity_id == document_id,
            )
            .order_by(func.lower(Tag.name))
        )
    ).all()
    return [str(row.id) for row in rows], tuple(str(row.name) for row in rows)


def _keywords(title: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[\w\u3400-\u9fff]+", title, flags=re.UNICODE):
        normalized = token.strip().casefold()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)
        if len(values) >= _KEYWORD_LIMIT:
            break
    return values


async def _candidate_notes(
    db: AsyncSession,
    document: DriveDocument,
    project_ids: list[str],
    tag_ids: list[str],
) -> list[RelatedNoteCandidate]:
    linked_note_ids = list(
        (
            await db.execute(
                select(NoteDriveDocument.note_id).where(
                    NoteDriveDocument.drive_document_id == document.id
                )
            )
        ).scalars().all()
    )

    shared_note_ids: list[str] = []
    if tag_ids:
        shared_note_ids = list(
            (
                await db.execute(
                    select(EntityTag.entity_id).where(
                        EntityTag.entity_type == "note",
                        EntityTag.tag_id.in_(tag_ids),
                    )
                )
            ).scalars().all()
        )

    clauses = []
    if project_ids:
        clauses.append(Note.project_id.in_(project_ids))
    if shared_note_ids:
        clauses.append(Note.id.in_(shared_note_ids))
    for keyword in _keywords(document.name):
        clauses.extend(
            (
                func.lower(Note.title).contains(keyword, autoescape=True),
                func.lower(Note.body).contains(keyword, autoescape=True),
            )
        )
    if not clauses:
        return []

    statement = select(Note).where(or_(*clauses))
    if linked_note_ids:
        statement = statement.where(~Note.id.in_(linked_note_ids))
    notes = list(
        (
            await db.execute(
                statement.order_by(Note.updated_at.desc()).limit(_MAX_CANDIDATES)
            )
        ).scalars().all()
    )
    return [
        RelatedNoteCandidate(
            note_id=note.id,
            title=(note.title or "")[:_MAX_NOTE_TITLE],
            snippet=(note.body or "")[:_MAX_NOTE_SNIPPET],
            project_id=note.project_id,
        )
        for note in notes
    ]


async def _add_ai_tags(
    db: AsyncSession,
    document_id: str,
    tag_names: list[str],
) -> None:
    for raw_name in tag_names:
        name = raw_name.strip()
        if not name or len(name) > 255:
            continue
        tag = (
            await db.execute(
                select(Tag).where(func.lower(Tag.name) == name.casefold()).limit(1)
            )
        ).scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=name)
            db.add(tag)
            await db.flush()
        relation = await db.get(
            EntityTag,
            {
                "entity_type": "drive_document",
                "entity_id": document_id,
                "tag_id": tag.id,
            },
        )
        if relation is None:
            db.add(
                EntityTag(
                    entity_type="drive_document",
                    entity_id=document_id,
                    tag_id=tag.id,
                )
            )


def _decode_suggested_tags(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if isinstance(item, str)]


async def _run_view(
    db: AsyncSession,
    run: DriveDocumentEnrichmentRun,
    *,
    cache_hit: bool,
) -> dict[str, object]:
    suggestions = list(
        (
            await db.execute(
                select(DriveNoteLinkSuggestion)
                .where(DriveNoteLinkSuggestion.enrichment_run_id == run.id)
                .order_by(
                    DriveNoteLinkSuggestion.confidence.desc(),
                    DriveNoteLinkSuggestion.note_id,
                )
            )
        ).scalars().all()
    )
    return {
        "id": run.id,
        "drive_document_id": run.drive_document_id,
        "content_fingerprint": run.content_fingerprint,
        "provider": run.provider,
        "model": run.model,
        "status": run.status,
        "suggested_tags": _decode_suggested_tags(run.suggested_tags_json),
        "note_suggestions": suggestions,
        "error_code": run.error_code,
        "cache_hit": cache_hit,
        "created_at": run.created_at,
    }


async def enrich_document(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    *,
    force: bool = False,
    provider: AIEnrichmentProvider | None = None,
    document_text: str | None = None,
) -> dict[str, object]:
    document = await drive_documents.get_document(db, user_sub, document_id)
    enrichment_settings = await get_enrichment_settings(db, user_sub)

    project_ids: list[str] = []
    project_context: tuple[str, ...] = ()
    tag_ids: list[str] = []
    existing_tags: tuple[str, ...] = ()
    candidates: list[RelatedNoteCandidate] = []
    if enrichment_settings.allow_document_content:
        project_ids, project_context = await _document_projects(db, document.id)
        tag_ids, existing_tags = await _document_tags(db, document.id)
        if enrichment_settings.note_suggestions_enabled:
            candidates = await _candidate_notes(
                db,
                document,
                project_ids,
                tag_ids,
            )

    context = DocumentEnrichmentContext(
        document_id=document.id,
        title=document.name,
        mime_type=document.mime_type,
        document_text=(document_text or "")[:12000] or None,
        project_context=project_context,
        existing_tags=existing_tags,
        max_related_notes=enrichment_settings.max_related_note_suggestions,
    )
    fingerprint = compute_enrichment_fingerprint(
        context,
        candidates,
        enable_tags=enrichment_settings.auto_tags_enabled,
        enable_related_notes=enrichment_settings.note_suggestions_enabled,
    )

    if not force:
        cached = (
            await db.execute(
                select(DriveDocumentEnrichmentRun)
                .where(
                    DriveDocumentEnrichmentRun.drive_document_id == document.id,
                    DriveDocumentEnrichmentRun.content_fingerprint == fingerprint,
                    DriveDocumentEnrichmentRun.status == "succeeded",
                )
                .order_by(DriveDocumentEnrichmentRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if cached is not None:
            return await _run_view(db, cached, cache_hit=True)

    resolved_provider = provider or get_ai_enrichment_provider()
    outcome = await execute_provider_enrichment(
        resolved_provider,
        context,
        candidates,
        allow_ai=enrichment_settings.allow_document_content,
        enable_tags=enrichment_settings.auto_tags_enabled,
        enable_related_notes=enrichment_settings.note_suggestions_enabled,
    )
    tag_names = [item.name for item in outcome.tags]
    run = DriveDocumentEnrichmentRun(
        id=str(uuid.uuid4()),
        drive_document_id=document.id,
        content_fingerprint=fingerprint,
        provider=outcome.provider,
        model=outcome.model,
        status=outcome.status,
        suggested_tags_json=json.dumps(tag_names, ensure_ascii=False, separators=(",", ":")),
        error_code=outcome.error_code,
    )
    db.add(run)
    await db.flush()

    if outcome.status in {"succeeded", "partial"} and tag_names:
        await _add_ai_tags(db, document.id, tag_names)

    allowed_note_ids = {item.note_id for item in candidates}
    for suggestion in outcome.related_notes:
        if suggestion.note_id not in allowed_note_ids:
            continue
        db.add(
            DriveNoteLinkSuggestion(
                id=str(uuid.uuid4()),
                enrichment_run_id=run.id,
                drive_document_id=document.id,
                note_id=suggestion.note_id,
                confidence=suggestion.confidence,
                reason=suggestion.reason,
                decision="pending",
            )
        )

    await db.commit()
    await db.refresh(run)
    return await _run_view(db, run, cache_hit=False)


async def get_latest_enrichment(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
) -> dict[str, object] | None:
    document = await drive_documents.get_document(db, user_sub, document_id)
    run = (
        await db.execute(
            select(DriveDocumentEnrichmentRun)
            .where(DriveDocumentEnrichmentRun.drive_document_id == document.id)
            .order_by(DriveDocumentEnrichmentRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return None
    return await _run_view(db, run, cache_hit=False)


async def decide_note_suggestion(
    db: AsyncSession,
    user_sub: str,
    suggestion_id: str,
    decision: str,
) -> DriveNoteLinkSuggestion:
    suggestion = (
        await db.execute(
            select(DriveNoteLinkSuggestion)
            .join(
                DriveDocument,
                DriveDocument.id == DriveNoteLinkSuggestion.drive_document_id,
            )
            .where(
                DriveNoteLinkSuggestion.id == suggestion_id,
                DriveDocument.user_sub == user_sub,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(404, "Drive Note suggestion not found")

    if suggestion.decision == decision:
        return suggestion
    if suggestion.decision != "pending":
        raise HTTPException(409, "Drive Note suggestion decision is already final")

    if decision == "accepted":
        relation = await db.get(
            NoteDriveDocument,
            {
                "note_id": suggestion.note_id,
                "drive_document_id": suggestion.drive_document_id,
            },
        )
        if relation is None:
            db.add(
                NoteDriveDocument(
                    note_id=suggestion.note_id,
                    drive_document_id=suggestion.drive_document_id,
                    relation_type="related",
                    link_source="ai_accepted",
                )
            )

    suggestion.decision = decision
    suggestion.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion
