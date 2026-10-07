#!/usr/bin/env python3
"""Live production-provider smoke acceptance using synthetic Drive context only.

The immutable release image resolves the provider from its runtime secret bundle.
No user/Drive/database data is read. A successful run proves the configured
external provider can complete both structured-output enrichment stages.
"""

from __future__ import annotations

import asyncio

from app import config
from app.services.ai_enrichment_provider import (
    AIProviderError,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    UnavailableAIEnrichmentProvider,
    get_ai_enrichment_provider,
)


EXIT_NOT_CONFIGURED = 84
EXIT_PROVIDER_FAILURE = 85
EXIT_MODEL_MISSING = 86
EXIT_API_KEY_MISSING = 87
EXIT_BASE_URL_MISSING = 88
EXIT_PROVIDER_FAILURE_MASK_BASE = 90
_PROVIDER_FAILURE_BITS = {
    "gemini": 1,
    "openrouter": 2,
    "groq": 4,
    "openai": 8,
}


def _exit_code_for_unavailable_provider(
    *,
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
) -> int:
    mask = 0
    if provider.strip().casefold() not in {"openai", "gemini", "openrouter", "groq"}:
        mask |= 1
    if not model.strip():
        mask |= 2
    if not api_key.strip():
        mask |= 4
    if not base_url.strip():
        mask |= 8

    if mask == 0:
        return EXIT_NOT_CONFIGURED
    if mask == 1:
        return EXIT_NOT_CONFIGURED
    if mask == 2:
        return EXIT_MODEL_MISSING
    if mask == 4:
        return EXIT_API_KEY_MISSING
    if mask == 8:
        return EXIT_BASE_URL_MISSING
    return 100 + mask


def _unavailable_reason(exit_code: int) -> str:
    return {
        EXIT_NOT_CONFIGURED: "provider_not_supported_or_unavailable",
        EXIT_MODEL_MISSING: "model_missing",
        EXIT_API_KEY_MISSING: "api_key_missing",
        EXIT_BASE_URL_MISSING: "base_url_missing",
    }.get(exit_code, "production_provider_not_configured")


async def run_acceptance(*, provider_name: str | None = None, model: str | None = None) -> None:
    provider = get_ai_enrichment_provider(provider=provider_name, model=model)
    if isinstance(provider, UnavailableAIEnrichmentProvider):
        exit_code = _exit_code_for_unavailable_provider(
            provider=provider_name or str(config.settings.ai_enrichment_provider or ""),
            model=model if model is not None else str(config.settings.ai_enrichment_model or ""),
            api_key=str(getattr(config.settings, f"{provider_name or config.settings.ai_enrichment_provider}_api_key", "") or ""),
            base_url=str(config.settings.openai_base_url or "") if (provider_name or config.settings.ai_enrichment_provider) == "openai" else "vendor_endpoint",
        )
        print(
            "drive_external_ai_integration=NOT_VERIFIED "
            f"provider={provider_name or config.settings.ai_enrichment_provider} "
            f"model={model if model is not None else config.settings.ai_enrichment_model} "
            f"reason={_unavailable_reason(exit_code)}",
            flush=True,
        )
        raise SystemExit(exit_code)

    context = DocumentEnrichmentContext(
        document_id="acceptance-synthetic-drive-document",
        title="Synthetic Drive production acceptance document",
        mime_type="application/vnd.google-apps.document",
        document_text=(
            "Synthetic acceptance content about quarterly planning, action items, "
            "and project research. This text contains no user or production data."
        ),
        project_context=("Synthetic acceptance project",),
        existing_tags=("acceptance-existing",),
        max_related_notes=1,
    )
    candidates = [
        RelatedNoteCandidate(
            note_id="acceptance-synthetic-note",
            title="Synthetic planning note",
            snippet="Synthetic note about quarterly planning and research action items.",
            project_id="acceptance-synthetic-project",
        )
    ]

    try:
        tags = await provider.suggest_tags(context)
        notes = await provider.rank_related_notes(context, candidates)
    except AIProviderError as exc:
        print(
            "drive_external_ai_integration=FAIL "
            f"provider={provider_name or provider.provider_name or 'unknown'} "
            f"model={model if model is not None else provider.model_name or 'unknown'} "
            f"reason={exc.code}",
            flush=True,
        )
        raise SystemExit(EXIT_PROVIDER_FAILURE) from exc
    except Exception as exc:
        print(
            "drive_external_ai_integration=FAIL "
            f"provider={provider_name or provider.provider_name or 'unknown'} "
            f"model={model if model is not None else provider.model_name or 'unknown'} "
            f"reason={type(exc).__name__}",
            flush=True,
        )
        raise SystemExit(EXIT_PROVIDER_FAILURE) from exc

    if not isinstance(tags, list) or not isinstance(notes, list):
        print(
            "drive_external_ai_integration=FAIL "
            f"provider={provider_name or provider.provider_name or 'unknown'} "
            f"model={model if model is not None else provider.model_name or 'unknown'} "
            "reason=invalid_provider_result",
            flush=True,
        )
        raise SystemExit(EXIT_PROVIDER_FAILURE)

    provider_name = provider.provider_name or "unknown"
    model_name = provider.model_name or "unknown"
    print(
        "drive_external_ai_integration=PASS "
        f"provider={provider_name} model={model_name} "
        f"served_models={','.join(sorted(getattr(provider, 'served_models', ())))} "
        f"tag_results={len(tags)} note_results={len(notes)}",
        flush=True,
    )


async def run_configured_providers() -> None:
    # Test every configured provider even when an earlier provider fails. This
    # prevents a healthy fallback from hiding a broken primary while still
    # leaving provider-specific task-exit evidence when Cloud Logging is not
    # readable by the deployment identity.
    configured = [
        (config.settings.ai_enrichment_provider, config.settings.ai_enrichment_model),
    ]
    for tier in ("fallback", "tertiary"):
        name = getattr(config.settings, f"ai_enrichment_{tier}_provider")
        if name:
            configured.append(
                (name, getattr(config.settings, f"ai_enrichment_{tier}_model"))
            )

    provider_failure_mask = 0
    configuration_failures: list[tuple[str, int]] = []
    provider_failures: list[str] = []
    for name, model in configured:
        normalized_name = str(name or "").strip().casefold()
        try:
            await run_acceptance(provider_name=name, model=model)
        except SystemExit as exc:
            exit_code = int(exc.code or EXIT_PROVIDER_FAILURE)
            if exit_code == EXIT_PROVIDER_FAILURE:
                provider_failures.append(normalized_name or "unknown")
                provider_failure_mask |= _PROVIDER_FAILURE_BITS.get(normalized_name, 0)
            else:
                configuration_failures.append((normalized_name or "unknown", exit_code))

    if configuration_failures:
        summary = ",".join(f"{name}:{code}" for name, code in configuration_failures)
        print(f"drive_external_ai_summary=FAIL configuration_failures={summary}", flush=True)
        raise SystemExit(configuration_failures[0][1])

    if provider_failures:
        summary = ",".join(provider_failures)
        print(f"drive_external_ai_summary=FAIL provider_failures={summary}", flush=True)
        if provider_failure_mask:
            raise SystemExit(EXIT_PROVIDER_FAILURE_MASK_BASE + provider_failure_mask)
        raise SystemExit(EXIT_PROVIDER_FAILURE)

    print(
        "drive_external_ai_summary=PASS providers="
        + ",".join(str(name).strip().casefold() for name, _ in configured),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(run_configured_providers())
