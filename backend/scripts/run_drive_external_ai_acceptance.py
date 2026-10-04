#!/usr/bin/env python3
"""Live production-provider smoke acceptance using synthetic Drive context only.

The immutable release image resolves the provider from its runtime secret bundle.
No user/Drive/database data is read. A successful run proves the configured
external provider can complete both structured-output enrichment stages.
"""

from __future__ import annotations

import asyncio

from app.services.ai_enrichment_provider import (
    AIProviderError,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    UnavailableAIEnrichmentProvider,
    get_ai_enrichment_provider,
)


EXIT_NOT_CONFIGURED = 84
EXIT_PROVIDER_FAILURE = 85


async def run_acceptance() -> None:
    provider = get_ai_enrichment_provider()
    if isinstance(provider, UnavailableAIEnrichmentProvider):
        print(
            "drive_external_ai_integration=NOT_VERIFIED reason=production_provider_not_configured",
            flush=True,
        )
        raise SystemExit(EXIT_NOT_CONFIGURED)

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
            f"drive_external_ai_integration=FAIL reason={exc.code}",
            flush=True,
        )
        raise SystemExit(EXIT_PROVIDER_FAILURE) from exc
    except Exception as exc:
        print(
            f"drive_external_ai_integration=FAIL reason={type(exc).__name__}",
            flush=True,
        )
        raise SystemExit(EXIT_PROVIDER_FAILURE) from exc

    if not isinstance(tags, list) or not isinstance(notes, list):
        print("drive_external_ai_integration=FAIL reason=invalid_provider_result", flush=True)
        raise SystemExit(EXIT_PROVIDER_FAILURE)

    provider_name = provider.provider_name or "unknown"
    model_name = provider.model_name or "unknown"
    print(
        "drive_external_ai_integration=PASS "
        f"provider={provider_name} model={model_name} tag_results={len(tags)} note_results={len(notes)}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(run_acceptance())
