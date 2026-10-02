from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentEnrichmentContext:
    document_id: str
    title: str
    mime_type: str
    document_text: str | None
    project_context: tuple[str, ...] = ()
    existing_tags: tuple[str, ...] = ()
    max_related_notes: int = 5


@dataclass(frozen=True, slots=True)
class RelatedNoteCandidate:
    note_id: str
    title: str
    snippet: str
    project_id: str | None


@dataclass(frozen=True, slots=True)
class TagSuggestion:
    name: str
    confidence: float


@dataclass(frozen=True, slots=True)
class RelatedNoteSuggestion:
    note_id: str
    confidence: float
    reason: str


@dataclass(frozen=True, slots=True)
class ProviderEnrichmentOutcome:
    status: str
    provider: str | None
    model: str | None
    tags: tuple[TagSuggestion, ...]
    related_notes: tuple[RelatedNoteSuggestion, ...]
    error_code: str | None


class AIProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AIEnrichmentProvider(ABC):
    provider_name: str | None = None
    model_name: str | None = None

    @abstractmethod
    async def suggest_tags(self, document_context: DocumentEnrichmentContext) -> list[TagSuggestion]:
        raise NotImplementedError

    @abstractmethod
    async def rank_related_notes(
        self,
        document_context: DocumentEnrichmentContext,
        candidate_notes: list[RelatedNoteCandidate],
    ) -> list[RelatedNoteSuggestion]:
        raise NotImplementedError


class UnavailableAIEnrichmentProvider(AIEnrichmentProvider):
    provider_name = "disabled"
    model_name = None

    async def suggest_tags(self, document_context: DocumentEnrichmentContext) -> list[TagSuggestion]:
        del document_context
        raise AIProviderError("provider_unavailable")

    async def rank_related_notes(
        self,
        document_context: DocumentEnrichmentContext,
        candidate_notes: list[RelatedNoteCandidate],
    ) -> list[RelatedNoteSuggestion]:
        del document_context, candidate_notes
        raise AIProviderError("provider_unavailable")


def get_ai_enrichment_provider() -> AIEnrichmentProvider:
    return UnavailableAIEnrichmentProvider()


def compute_enrichment_fingerprint(
    document_context: DocumentEnrichmentContext,
    candidate_notes: list[RelatedNoteCandidate] | tuple[RelatedNoteCandidate, ...] = (),
    *,
    enable_tags: bool = True,
    enable_related_notes: bool = True,
) -> str:
    """Return a stable fingerprint for source/context inputs only.

    Existing Tags and the current candidate-Note snapshot are deliberately not
    part of cache identity because enrichment itself can change those values.
    Including them makes a successful run invalidate its own cache on the next
    request. They remain available to provider adapters as prompt context.
    """

    del candidate_notes
    payload = {
        "contract": "drive-ai-enrichment-v1",
        "document_id": document_context.document_id,
        "title": document_context.title.strip(),
        "mime_type": document_context.mime_type.strip(),
        "document_text": (document_context.document_text or "").strip(),
        "project_context": sorted(
            {value.strip() for value in document_context.project_context if value.strip()}
        ),
        "max_related_notes": document_context.max_related_notes,
        "enable_tags": enable_tags,
        "enable_related_notes": enable_related_notes,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _error_code(exc: BaseException) -> str:
    return exc.code if isinstance(exc, AIProviderError) and exc.code else "provider_error"


def _tags(values: list[TagSuggestion]) -> tuple[TagSuggestion, ...]:
    result: list[TagSuggestion] = []
    seen: set[str] = set()
    for value in values:
        name = value.name.strip()
        confidence = float(value.confidence)
        if not name or len(name) > 255 or not 0 <= confidence <= 1 or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        result.append(TagSuggestion(name=name, confidence=confidence))
        if len(result) == 8:
            break
    return tuple(result)


def _notes(
    values: list[RelatedNoteSuggestion],
    candidates: list[RelatedNoteCandidate],
    limit: int,
) -> tuple[RelatedNoteSuggestion, ...]:
    allowed = {item.note_id for item in candidates}
    result: list[RelatedNoteSuggestion] = []
    seen: set[str] = set()
    for value in values:
        confidence = float(value.confidence)
        reason = value.reason.strip()[:2000]
        if value.note_id not in allowed or value.note_id in seen or not 0 <= confidence <= 1 or not reason:
            continue
        seen.add(value.note_id)
        result.append(RelatedNoteSuggestion(value.note_id, confidence, reason))
    result.sort(key=lambda item: (-item.confidence, item.note_id))
    return tuple(result[:limit])


async def execute_provider_enrichment(
    provider: AIEnrichmentProvider,
    document_context: DocumentEnrichmentContext,
    candidate_notes: list[RelatedNoteCandidate],
    *,
    allow_ai: bool,
    enable_tags: bool,
    enable_related_notes: bool,
) -> ProviderEnrichmentOutcome:
    if not allow_ai:
        return ProviderEnrichmentOutcome(
            "skipped",
            provider.provider_name,
            provider.model_name,
            (),
            (),
            "consent_disabled",
        )
    if not enable_tags and not enable_related_notes:
        return ProviderEnrichmentOutcome(
            "skipped",
            provider.provider_name,
            provider.model_name,
            (),
            (),
            "enrichment_disabled",
        )

    tags: tuple[TagSuggestion, ...] = ()
    notes: tuple[RelatedNoteSuggestion, ...] = ()
    failures: list[str] = []
    successes = 0

    if enable_tags:
        try:
            tags = _tags(await provider.suggest_tags(document_context))
            successes += 1
        except Exception as exc:
            failures.append(_error_code(exc))

    if enable_related_notes:
        try:
            notes = _notes(
                await provider.rank_related_notes(document_context, candidate_notes),
                candidate_notes,
                document_context.max_related_notes,
            )
            successes += 1
        except Exception as exc:
            failures.append(_error_code(exc))

    if not failures:
        status, error_code = "succeeded", None
    elif successes:
        status = "partial"
        error_code = failures[0] if len(failures) == 1 else "multiple_provider_failures"
    else:
        status = "failed"
        error_code = failures[0] if len(failures) == 1 else "multiple_provider_failures"
    return ProviderEnrichmentOutcome(
        status,
        provider.provider_name,
        provider.model_name,
        tags,
        notes,
        error_code,
    )
