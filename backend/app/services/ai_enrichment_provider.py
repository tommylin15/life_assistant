from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app import config
from app.db.session import SessionLocal
from app.models.ai_provider_preference import AIProviderPreference


TAG_CONFIDENCE_THRESHOLD = 0.80
RELATED_NOTE_CONFIDENCE_THRESHOLD = 0.60
_OPENAI_TIMEOUT_SECONDS = 30.0
_TRANSIENT_RETRY_DELAYS_SECONDS = (1.0,)
_GEMINI_DISCOVERY_RETRY_DELAYS_SECONDS = (1.0, 3.0)
_GEMINI_MODEL_CYCLE_RETRY_DELAYS_SECONDS = (2.0, 5.0)


def _is_transient_http_status(status_code: int) -> bool:
    return status_code in {408, 429} or 500 <= status_code <= 599


async def load_ai_provider_preference(provider: str) -> str | None:
    normalized = provider.strip().casefold()
    if not normalized:
        return None
    try:
        async with SessionLocal() as db:
            preference = await db.get(AIProviderPreference, normalized)
            if preference is None:
                return None
            model = preference.preferred_model.strip()
            return model or None
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "drive_ai_preference_load_failed provider=%s error=%s",
            normalized,
            type(exc).__name__,
        )
        return None


async def remember_ai_provider_preference(provider: str, model: str) -> None:
    normalized_provider = provider.strip().casefold()
    normalized_model = model.strip()
    if not normalized_provider or not normalized_model:
        return
    try:
        async with SessionLocal() as db:
            preference = await db.get(AIProviderPreference, normalized_provider)
            now = datetime.now(timezone.utc)
            if preference is None:
                db.add(
                    AIProviderPreference(
                        provider=normalized_provider,
                        preferred_model=normalized_model,
                        updated_at=now,
                    )
                )
            else:
                preference.preferred_model = normalized_model
                preference.updated_at = now
            await db.commit()
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "drive_ai_preference_store_failed provider=%s model=%s error=%s",
            normalized_provider,
            normalized_model,
            type(exc).__name__,
        )


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
    def __init__(self, code: str, *, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


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


def _setting(name: str, environment_name: str, default: str = "") -> str:
    """Resolve explicit Settings values first, then environment fallback.

    The fallback keeps provider configuration compatible with the existing
    LIFE_ASSISTANT_BUNDLE loader, which exports parsed top-level bundle keys to
    the process environment without requiring a secret-format migration.
    """

    if hasattr(config.settings, name):
        value = getattr(config.settings, name)
        return str(value or "").strip()
    return os.environ.get(environment_name, default).strip()


def _json_schema_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": name,
        "strict": True,
        "schema": schema,
    }


def _document_payload(document_context: DocumentEnrichmentContext) -> dict[str, Any]:
    return {
        "title": document_context.title[:1000],
        "mime_type": document_context.mime_type[:255],
        "document_text": (document_context.document_text or "")[:12000],
        "project_context": [value[:500] for value in document_context.project_context[:20]],
        "existing_tags": [value[:255] for value in document_context.existing_tags[:50]],
    }


class OpenAIResponsesEnrichmentProvider(AIEnrichmentProvider):
    """Provider adapter for bounded Drive enrichment through Responses API.

    OAuth tokens, Google permissions, database metadata, and user identity are
    intentionally excluded. Only the already-approved enrichment context and
    bounded candidate-note snapshot are sent to the model.
    """

    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key.strip()
        self.model_name = model.strip()
        self._base_url = base_url.rstrip("/")
        if not self._api_key or not self.model_name or not self._base_url:
            raise ValueError("OpenAI enrichment provider requires complete configuration")

    async def _structured_response(
        self,
        *,
        instructions: str,
        user_payload: dict[str, Any],
        format_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        request_body = {
            "model": self.model_name,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                user_payload,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    ],
                },
            ],
            "text": {"format": _json_schema_format(format_name, schema)},
        }
        try:
            async with httpx.AsyncClient(timeout=_OPENAI_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self._base_url}/responses",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
        except httpx.HTTPError as exc:
            raise AIProviderError("provider_http_error") from exc

        if response.status_code < 200 or response.status_code >= 300:
            raise AIProviderError("provider_http_error")

        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise AIProviderError("provider_invalid_output") from exc
        if not isinstance(payload, dict) or payload.get("status") != "completed":
            raise AIProviderError("provider_invalid_output")

        output_text: str | None = None
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                    ):
                        output_text = part["text"]
                        break
                if output_text is not None:
                    break
        if not output_text:
            raise AIProviderError("provider_invalid_output")

        try:
            parsed = json.loads(output_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("provider_invalid_output") from exc
        if not isinstance(parsed, dict):
            raise AIProviderError("provider_invalid_output")
        return parsed

    async def suggest_tags(self, document_context: DocumentEnrichmentContext) -> list[TagSuggestion]:
        parsed = await self._structured_response(
            instructions=(
                "Suggest concise reusable tags for the supplied Drive document. "
                "Use only the supplied document/project/tag context. Return confidence from 0 to 1."
            ),
            user_payload={"document": _document_payload(document_context)},
            format_name="drive_tag_suggestions",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tags": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string", "minLength": 1, "maxLength": 255},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                            "required": ["name", "confidence"],
                        },
                    }
                },
                "required": ["tags"],
            },
        )
        raw_tags = parsed.get("tags")
        if not isinstance(raw_tags, list):
            raise AIProviderError("provider_invalid_output")

        result: list[TagSuggestion] = []
        for item in raw_tags:
            if not isinstance(item, dict):
                raise AIProviderError("provider_invalid_output")
            name = item.get("name")
            confidence = item.get("confidence")
            if not isinstance(name, str) or not isinstance(confidence, (int, float)):
                raise AIProviderError("provider_invalid_output")
            result.append(TagSuggestion(name=name, confidence=float(confidence)))
        return result

    async def rank_related_notes(
        self,
        document_context: DocumentEnrichmentContext,
        candidate_notes: list[RelatedNoteCandidate],
    ) -> list[RelatedNoteSuggestion]:
        bounded_candidates = candidate_notes[:20]
        allowed_ids = {item.note_id for item in bounded_candidates}
        parsed = await self._structured_response(
            instructions=(
                "Rank only the supplied candidate notes for semantic relevance to the Drive document. "
                "Never invent note IDs. Return confidence from 0 to 1 and a short reason."
            ),
            user_payload={
                "document": _document_payload(document_context),
                "candidates": [
                    {
                        "note_id": item.note_id,
                        "title": item.title[:300],
                        "snippet": item.snippet[:500],
                        "project_id": item.project_id,
                    }
                    for item in bounded_candidates
                ],
                "max_related_notes": document_context.max_related_notes,
            },
            format_name="drive_related_note_suggestions",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "related_notes": {
                        "type": "array",
                        "maxItems": min(max(document_context.max_related_notes, 1), 20),
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "note_id": {"type": "string", "minLength": 1},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "reason": {"type": "string", "minLength": 1, "maxLength": 2000},
                            },
                            "required": ["note_id", "confidence", "reason"],
                        },
                    }
                },
                "required": ["related_notes"],
            },
        )
        raw_notes = parsed.get("related_notes")
        if not isinstance(raw_notes, list):
            raise AIProviderError("provider_invalid_output")

        result: list[RelatedNoteSuggestion] = []
        for item in raw_notes:
            if not isinstance(item, dict):
                raise AIProviderError("provider_invalid_output")
            note_id = item.get("note_id")
            confidence = item.get("confidence")
            reason = item.get("reason")
            if (
                not isinstance(note_id, str)
                or note_id not in allowed_ids
                or not isinstance(confidence, (int, float))
                or not isinstance(reason, str)
            ):
                raise AIProviderError("provider_invalid_output")
            result.append(
                RelatedNoteSuggestion(
                    note_id=note_id,
                    confidence=float(confidence),
                    reason=reason,
                )
            )
        return result


class ChatCompletionsEnrichmentProvider(OpenAIResponsesEnrichmentProvider):
    """Reuse enrichment schemas for Gemini/OpenRouter/Groq's compatible HTTP API."""

    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        retry_delays_seconds: tuple[float, ...] | None = None,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self.provider_name = provider
        self.served_models: set[str] = set()
        self._retry_delays_seconds = (
            _TRANSIENT_RETRY_DELAYS_SECONDS
            if retry_delays_seconds is None
            else retry_delays_seconds
        )

    async def _structured_response(
        self, *, instructions: str, user_payload: dict[str, Any],
        format_name: str, schema: dict[str, Any],
    ) -> dict[str, Any]:
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": format_name, "strict": True, "schema": schema},
            },
        }
        if self.provider_name == "gemini":
            # Gemini reasoning models cannot always disable thinking entirely.
            # Low effort keeps bounded enrichment responsive while preserving
            # structured-output behavior through the OpenAI compatibility API.
            body["reasoning_effort"] = "low"
        if self.provider_name == "openrouter":
            # ponytail: free endpoints support JSON mode, not always JSON Schema;
            # keep the schema in the prompt and validate tags/candidate IDs locally.
            body["response_format"] = {"type": "json_object"}
            body["messages"][0]["content"] += (
                " Return only a JSON object matching this schema: " + json.dumps(schema)
            )
            body["provider"] = {"require_parameters": True, "data_collection": "deny"}
        response = None
        last_http_error: httpx.HTTPError | None = None
        for attempt in range(len(self._retry_delays_seconds) + 1):
            try:
                async with httpx.AsyncClient(timeout=_OPENAI_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        json=body,
                    )
            except httpx.HTTPError as exc:
                last_http_error = exc
                if attempt >= len(self._retry_delays_seconds):
                    raise AIProviderError("provider_http_error") from exc
                logging.getLogger(__name__).warning(
                    "drive_ai_transient_retry provider=%s model=%s reason=transport attempt=%s",
                    self.provider_name,
                    self.model_name,
                    attempt + 1,
                )
            else:
                if (
                    not _is_transient_http_status(response.status_code)
                    or attempt >= len(self._retry_delays_seconds)
                ):
                    break
                logging.getLogger(__name__).warning(
                    "drive_ai_transient_retry provider=%s model=%s status=%s attempt=%s",
                    self.provider_name,
                    self.model_name,
                    response.status_code,
                    attempt + 1,
                )
            await asyncio.sleep(self._retry_delays_seconds[attempt])

        if response is None:
            raise AIProviderError("provider_http_error") from last_http_error
        if not 200 <= response.status_code < 300:
            raise AIProviderError(
                "provider_http_error",
                status_code=response.status_code,
            )
        try:
            choice = response.json()["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise AIProviderError("provider_invalid_output")
            parsed = json.loads(choice["message"]["content"])
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            raise AIProviderError("provider_invalid_output") from exc
        if not isinstance(parsed, dict):
            raise AIProviderError("provider_invalid_output")
        self.served_models.add(self.model_name)
        return parsed


# The omniAgent shared Codex service is a private text-only inference endpoint.
# Never install Codex CLI or access its OAuth Secret from this consumer.
_CODEX_PROJECT = "life-assistant"
_CODEX_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)
_CODEX_MAX_PROMPT_BYTES = 16 * 1024
_CODEX_MAX_RESULT_CHARS = 32000
_CODEX_LOCAL_QUEUE = asyncio.Semaphore(1)


def codex_owner_uuid(user_sub: str) -> str:
    """Stable non-reversible project-scoped UUID from authenticated Google sub."""
    if not user_sub or not user_sub.strip():
        raise ValueError("missing authenticated user sub")
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "life-assistant:google-sub:" + user_sub.strip()))


class SharedCodexEnrichmentProvider(OpenAIResponsesEnrichmentProvider):
    """Reuse existing tag/related-note strict downstream validation.

    Owner is derived by the server from the authenticated user, never the client
    request body. Auth is a scoped GCP ID token minted for the dedicated caller.
    """

    provider_name = "codex"

    def __init__(self, *, owner_id: str, model: str = "") -> None:
        try:
            self._owner_id = str(uuid.UUID(owner_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("invalid authenticated Codex owner UUID") from exc
        self._model = model.strip()
        self.model_name = self._model or "shared-default"
        self._base_url = str(config.settings.codex_shared_base_url).rstrip("/")
        self._caller_sa = str(config.settings.codex_shared_caller_service_account)
        self.served_models: set[str] = set()

    async def _mint_google_id_token(self, client: httpx.AsyncClient) -> str:
        """Metadata access token only for calling IAMCredentials:generateIdToken."""
        try:
            metadata = await client.get(
                _CODEX_METADATA_TOKEN_URL,
                headers={"Metadata-Flavor": "Google"},
            )
            if metadata.status_code != 200:
                raise AIProviderError("provider_auth_unavailable", status_code=metadata.status_code)
            source_token = metadata.json().get("access_token")
            if not isinstance(source_token, str) or not source_token:
                raise AIProviderError("provider_auth_unavailable")
            identity = await client.post(
                "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                + self._caller_sa + ":generateIdToken",
                headers={"Authorization": "Bearer " + source_token},
                json={"audience": self._base_url, "includeEmail": True},
            )
        except httpx.HTTPError as exc:
            raise AIProviderError("provider_auth_unavailable") from exc
        if identity.status_code != 200:
            raise AIProviderError("provider_auth_unavailable", status_code=identity.status_code)
        try:
            result = identity.json()["token"]
        except (KeyError, ValueError, TypeError) as exc:
            raise AIProviderError("provider_auth_unavailable") from exc
        if not isinstance(result, str) or not result:
            raise AIProviderError("provider_auth_unavailable")
        return result

    async def _structured_response(
        self,
        *,
        instructions: str,
        user_payload: dict[str, Any],
        format_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._base_url.startswith("https://") or not self._caller_sa.endswith(
            "@gen-lang-client-0593591102.iam.gserviceaccount.com"
        ):
            raise AIProviderError("provider_unavailable")

        prompt = (
            instructions + "\\nReturn ONLY a JSON object matching the exact schema "
            + format_name + ". Do not run tools. Schema: "
            + json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
            + "\\nSupplied input: "
            + json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))
        )
        if len(prompt.encode("utf-8")) > _CODEX_MAX_PROMPT_BYTES:
            raise AIProviderError("provider_request_too_large")

        request_id = str(uuid.uuid4())
        payload: dict[str, str] = {
            "project": _CODEX_PROJECT,
            "ownerId": self._owner_id,
            "requestId": request_id,
            "prompt": prompt,
        }
        if self._model:
            payload["model"] = self._model

        # Shared service supports one concurrent turn. Queue locally, and on
        # a genuine 429 retry once with a bounded backoff (read-only prompt).
        timeout = httpx.Timeout(connect=10.0, read=175.0, write=15.0, pool=15.0)
        async with _CODEX_LOCAL_QUEUE:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    identity_token = await self._mint_google_id_token(client)
                    response = await client.post(
                        self._base_url + "/v1/codex/execute",
                        headers={
                            "Authorization": "Bearer " + identity_token,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    if response.status_code == 429:
                        logging.getLogger(__name__).warning(
                            "drive_codex_backpressure request_id=%s status=429",
                            request_id,
                        )
                        await asyncio.sleep(2)
                        response = await client.post(
                            self._base_url + "/v1/codex/execute",
                            headers={
                                "Authorization": "Bearer " + identity_token,
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )
            except httpx.TimeoutException as exc:
                raise AIProviderError("provider_http_error", status_code=408) from exc
            except httpx.HTTPError as exc:
                raise AIProviderError("provider_http_error") from exc

        logging.getLogger(__name__).info(
            "drive_codex_response request_id=%s status_code=%s",
            request_id,
            response.status_code,
        )
        if response.status_code != 200:
            raise AIProviderError("provider_http_error", status_code=response.status_code)
        try:
            body = response.json()
            if (
                not isinstance(body, dict)
                or body.get("status") != "completed"
                or body.get("project") != _CODEX_PROJECT
                or body.get("ownerId") != self._owner_id
                or body.get("requestId") != request_id
            ):
                raise ValueError("invalid response envelope")
            response_ids = body.get("providerIds")
            if not isinstance(response_ids, dict) or any(
                not isinstance(response_ids.get(key), str)
                or not response_ids[key].strip()
                for key in ("threadId", "turnId")
            ):
                raise ValueError("invalid response trace")
            raw_text = body["result"]["text"]
            if (
                not isinstance(raw_text, str)
                or not raw_text.strip()
                or len(raw_text) > _CODEX_MAX_RESULT_CHARS
            ):
                raise ValueError("invalid response text")
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("invalid JSON schema result")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise AIProviderError("provider_invalid_output") from exc
        self.served_models.add(self.model_name)
        return parsed


class FallbackAIEnrichmentProvider(AIEnrichmentProvider):
    """One fallback per stage; metadata identifies the configured routing policy."""

    def __init__(self, primary: AIEnrichmentProvider, fallback: AIEnrichmentProvider) -> None:
        self.primary, self.fallback = primary, fallback
        self.provider_name = f"{primary.provider_name}+{fallback.provider_name}"
        self.model_name = f"{primary.model_name}+{fallback.model_name}"

    async def suggest_tags(self, document_context):
        try:
            return await self.primary.suggest_tags(document_context)
        except AIProviderError as exc:
            logging.getLogger(__name__).warning("drive_ai_fallback primary=%s stage=tags reason=%s status=%s", self.primary.provider_name, exc.code, exc.status_code)
            return await self.fallback.suggest_tags(document_context)

    async def rank_related_notes(self, document_context, candidate_notes):
        try:
            return await self.primary.rank_related_notes(document_context, candidate_notes)
        except AIProviderError as exc:
            logging.getLogger(__name__).warning("drive_ai_fallback primary=%s stage=related_notes reason=%s status=%s", self.primary.provider_name, exc.code, exc.status_code)
            return await self.fallback.rank_related_notes(document_context, candidate_notes)


class LatestGeminiEnrichmentProvider(ChatCompletionsEnrichmentProvider):
    """Prefer the last successful stable Flash model, then probe newest stable models."""

    def __init__(self, *, api_key: str) -> None:
        super().__init__(
            provider="gemini",
            api_key=api_key,
            model="latest-3-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            retry_delays_seconds=(),
        )
        self._models: list[str] | None = None
        self._available_models: list[str] | None = None
        self._preferred_model: str | None = None
        self._preference_loaded = False

    async def _discover_models(self) -> None:
        response = None
        last_http_error: httpx.HTTPError | None = None
        for attempt in range(len(_GEMINI_DISCOVERY_RETRY_DELAYS_SECONDS) + 1):
            try:
                async with httpx.AsyncClient(timeout=_OPENAI_TIMEOUT_SECONDS) as client:
                    response = await client.get(
                        "https://generativelanguage.googleapis.com/v1beta/models",
                        headers={"x-goog-api-key": self._api_key},
                        params={"pageSize": 1000},
                    )
            except httpx.HTTPError as exc:
                last_http_error = exc
                if attempt >= len(_GEMINI_DISCOVERY_RETRY_DELAYS_SECONDS):
                    raise AIProviderError("provider_http_error") from exc
                logging.getLogger(__name__).warning(
                    "drive_ai_transient_retry provider=gemini model=models-list "
                    "reason=transport attempt=%s",
                    attempt + 1,
                )
            else:
                if (
                    not _is_transient_http_status(response.status_code)
                    or attempt >= len(_GEMINI_DISCOVERY_RETRY_DELAYS_SECONDS)
                ):
                    break
                logging.getLogger(__name__).warning(
                    "drive_ai_transient_retry provider=gemini model=models-list "
                    "status=%s attempt=%s",
                    response.status_code,
                    attempt + 1,
                )
            await asyncio.sleep(_GEMINI_DISCOVERY_RETRY_DELAYS_SECONDS[attempt])

        if response is None:
            raise AIProviderError("provider_http_error") from last_http_error
        if response.status_code != 200:
            raise AIProviderError(
                "provider_http_error",
                status_code=response.status_code,
            )
        try:
            models = response.json()["models"]
            versions: dict[str, tuple[int, ...]] = {}
            for item in models:
                name = item.get("name", "").removeprefix("models/")
                match = re.fullmatch(r"gemini-(\d+(?:\.\d+)+)-flash", name)
                if match and "generateContent" in item.get("supportedGenerationMethods", []):
                    versions[name] = tuple(map(int, match.group(1).split(".")))
            self._available_models = sorted(versions, key=versions.get, reverse=True)
            self._models = self._available_models[:3]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise AIProviderError("provider_invalid_output") from exc
        if not self._models:
            raise AIProviderError("provider_unavailable")

    async def _load_persisted_preference(self) -> None:
        if self._preference_loaded:
            return
        self._preference_loaded = True
        preferred = await load_ai_provider_preference("gemini")
        if not preferred or preferred not in (self._available_models or ()):
            return
        self._preferred_model = preferred
        if preferred not in (self._models or ()):
            self._models = [preferred, *(self._models or ())]

    def _ordered_models(self) -> list[str]:
        models = list(self._models or ())
        if self._preferred_model in models:
            models.remove(self._preferred_model)
            models.insert(0, self._preferred_model)
        return models

    async def _structured_response(self, **kwargs) -> dict[str, Any]:
        if self._models is None:
            await self._discover_models()
        await self._load_persisted_preference()

        error = AIProviderError("provider_unavailable")
        for cycle in range(len(_GEMINI_MODEL_CYCLE_RETRY_DELAYS_SECONDS) + 1):
            transient_failure = False
            for model in self._ordered_models():
                candidate = ChatCompletionsEnrichmentProvider(
                    provider="gemini",
                    api_key=self._api_key,
                    model=model,
                    base_url=self._base_url,
                    retry_delays_seconds=(),
                )
                try:
                    result = await candidate._structured_response(**kwargs)
                    self._preferred_model = model
                    self.served_models.add(model)
                    await remember_ai_provider_preference("gemini", model)
                    logging.getLogger(__name__).info(
                        "drive_ai_provider_selected provider=gemini model=%s",
                        model,
                    )
                    return result
                except AIProviderError as exc:
                    error = exc
                    if exc.code == "provider_http_error" and exc.status_code == 429:
                        logging.getLogger(__name__).warning(
                            "drive_ai_rate_limited provider=gemini model=%s",
                            model,
                        )
                        raise
                    if (
                        exc.code == "provider_http_error"
                        and (
                            exc.status_code is None
                            or _is_transient_http_status(exc.status_code)
                        )
                    ):
                        transient_failure = True

            if (
                cycle >= len(_GEMINI_MODEL_CYCLE_RETRY_DELAYS_SECONDS)
                or not transient_failure
            ):
                break
            delay = _GEMINI_MODEL_CYCLE_RETRY_DELAYS_SECONDS[cycle]
            logging.getLogger(__name__).warning(
                "drive_ai_transient_retry provider=gemini model_cycle=%s delay_seconds=%s",
                cycle + 1,
                delay,
            )
            await asyncio.sleep(delay)

        raise error


def get_ai_enrichment_provider(*, provider: str | None = None, model: str | None = None, owner_id: str | None = None) -> AIEnrichmentProvider:
    explicit = provider is not None
    provider = (provider if explicit else _setting("ai_enrichment_provider", "AI_ENRICHMENT_PROVIDER", "disabled")).casefold()
    model = model if model is not None else _setting("ai_enrichment_model", "AI_ENRICHMENT_MODEL")
    if provider == "codex":
        if not owner_id:
            return UnavailableAIEnrichmentProvider()
        return SharedCodexEnrichmentProvider(owner_id=owner_id, model=model or "")
    if provider not in {"openai", "gemini", "openrouter", "groq"}:
        return UnavailableAIEnrichmentProvider()

    api_key = _setting(f"{provider}_api_key", f"{provider.upper()}_API_KEY")
    base_url = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "openai": _setting("openai_base_url", "OPENAI_BASE_URL", "https://api.openai.com/v1"),
    }[provider]
    if not model or not api_key or not base_url:
        return UnavailableAIEnrichmentProvider()
    if provider == "gemini" and model == "latest-3-flash":
        resolved = LatestGeminiEnrichmentProvider(api_key=api_key)
    elif provider == "openai":
        resolved = OpenAIResponsesEnrichmentProvider(api_key=api_key, model=model, base_url=base_url)
    else:
        resolved = ChatCompletionsEnrichmentProvider(provider=provider, api_key=api_key, model=model, base_url=base_url)
    if not explicit:
        chain = [resolved]
        for tier in ("fallback", "tertiary"):
            name = _setting(f"ai_enrichment_{tier}_provider", f"AI_ENRICHMENT_{tier.upper()}_PROVIDER").casefold()
            if name:
                backup = get_ai_enrichment_provider(
                    provider=name,
                    model=_setting(f"ai_enrichment_{tier}_model", f"AI_ENRICHMENT_{tier.upper()}_MODEL"),
                )
                if isinstance(backup, UnavailableAIEnrichmentProvider):
                    return backup
                chain.append(backup)
        resolved = chain.pop()
        for primary in reversed(chain):
            resolved = FallbackAIEnrichmentProvider(primary, resolved)
        if config.settings.codex_primary_enabled:
            if not owner_id:
                # No authenticated subject means do not send a shared inference.
                return UnavailableAIEnrichmentProvider()
            codex = SharedCodexEnrichmentProvider(
                owner_id=owner_id,
                model=str(config.settings.codex_shared_model or ""),
            )
            resolved = FallbackAIEnrichmentProvider(codex, resolved)
    return resolved


def compute_enrichment_fingerprint(
    document_context: DocumentEnrichmentContext,
    candidate_notes: list[RelatedNoteCandidate] | tuple[RelatedNoteCandidate, ...] = (),
    *,
    enable_tags: bool = True,
    enable_related_notes: bool = True,
    provider: str | None = None,
    model: str | None = None,
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
        "provider": provider,
        "model": model,
        # ponytail: moving model policies reuse cache for at most one UTC day;
        # resolve concrete serving versions if immediate release invalidation is needed.
        "model_day": datetime.now(timezone.utc).date().isoformat()
        if model and ("latest" in model or "openrouter/free" in model) else None,
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
        if (
            not name
            or len(name) > 255
            or not TAG_CONFIDENCE_THRESHOLD <= confidence <= 1
            or name.casefold() in seen
        ):
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
        if (
            value.note_id not in allowed
            or value.note_id in seen
            or not RELATED_NOTE_CONFIDENCE_THRESHOLD <= confidence <= 1
            or not reason
        ):
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
