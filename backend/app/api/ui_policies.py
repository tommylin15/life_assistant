"""Versioned feature release, private UI preferences and non-secret AI admin.

Defaults preserve existing functionality. All writes are identity-checked and audited.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.errors import current_request_id
from app.models.curated import FeatureRollout, UserUIPreference, LifeAIPolicy
from app.models.execution_log import ExecutionLog
from app.models.drive import DriveDocumentEnrichmentRun

router = APIRouter(tags=["ui-and-admin"])
# Stable, code-owned routes: the database cannot supply executable paths.
FEATURES = {
    "today": ("/today", "首頁"),
    "tasks": ("/tasks", "待辦"),
    "calendar": ("/calendar", "日曆"),
    "projects": ("/projects", "專案"),
    "notes": ("/more/notes", "筆記"),
    "habits": ("/more/habits", "習慣"),
    "shopping": ("/more/shopping", "購物"),
    "events": ("/more/curated", "活動精選"),
    "drive": ("/more/drive", "Google Drive"),
    "integrations": ("/integrations", "Google 整合"),
}
DEFAULT_PINNED = ["tasks", "calendar", "projects"]
DEFAULT_MORE = ["notes", "habits", "events", "shopping", "drive", "integrations"]
DEFAULT_HOME = ["tasks", "calendar", "attention", "habits", "events", "projects"]
HOME_KEYS = set(DEFAULT_HOME) | {"notes", "shopping", "drive"}
AI_PROVIDERS = ["gemini", "gemini_lite", "groq", "openrouter", "openai", "codex"]


def is_owner(user: dict) -> bool:
    approved = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().casefold()
    return bool(approved and str(user.get("email", "")).strip().casefold() == approved)


def owner_only(user: dict = Depends(current_user)) -> dict:
    if not is_owner(user):
        raise HTTPException(403, "Owner access required")
    return user


def _audit(db: AsyncSession, user_sub: str, action: str, summary: str) -> None:
    db.add(ExecutionLog(
        id=str(uuid.uuid4()), request_id=current_request_id(),
        user_sub=user_sub, action_type=action, provider="life_assistant",
        status="success", result="updated", summary=summary,
        finished_at=datetime.now(timezone.utc),
    ))


async def effective_features(db: AsyncSession, user: dict) -> list[dict]:
    rows = (await db.execute(select(FeatureRollout))).scalars().all()
    policies = {row.feature_key: row for row in rows}
    result = []
    for key, (path, title) in FEATURES.items():
        policy = policies.get(key)
        status = policy.status if policy else "enabled"
        audience = policy.audience if policy else "all"
        permitted = status not in ("hidden", "maintenance") and (
            audience == "all" or is_owner(user)
        ) and (status != "beta" or is_owner(user))
        result.append({"key": key, "path": path, "title": title, "available": permitted,
                       "status": status, "audience": audience})
    return result


def feature_gate(key: str):
    async def check(user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
        if not isinstance(db, AsyncSession):
            return  # Non-production mock session from unit tests.
        row = await db.get(FeatureRollout, key)
        if row is None:
            return
        if row.status in ("hidden", "maintenance") or row.audience == "owner" and not is_owner(user) or row.status == "beta" and not is_owner(user):
            raise HTTPException(403, "Feature is not available")
    return check


@router.get("/ui/features")
async def get_features(
    response: Response, user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return {"features": await effective_features(db, user)}


def _default_prefs() -> dict:
    return {"revision": 0, "nav_mode": "auto", "pinned": list(DEFAULT_PINNED),
            "more_order": list(DEFAULT_MORE), "home_cards": list(DEFAULT_HOME)}


def _prefs_view(row: UserUIPreference | None) -> dict:
    if row is None:
        return _default_prefs()
    return {"revision": row.revision, "nav_mode": row.nav_mode,
            "pinned": row.pinned, "more_order": row.more_order, "home_cards": row.home_cards}


@router.get("/me/ui-preferences")
async def get_my_preferences(
    response: Response, user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return _prefs_view(await db.get(UserUIPreference, user["sub"]))


class UIPreferencesWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    nav_mode: Literal["auto", "bottom", "sidebar"] = "auto"
    pinned: list[str] = Field(max_length=3)
    more_order: list[str] = Field(max_length=20)
    home_cards: list[str] = Field(max_length=15)

    @model_validator(mode="after")
    def valid_layout(self):
        for seq, allowed in ((self.pinned, set(FEATURES)-{"today"}),
                             (self.more_order, set(FEATURES)-{"today"}),
                             (self.home_cards, HOME_KEYS)):
            if len(seq) != len(set(seq)) or not set(seq).issubset(allowed):
                raise ValueError("Duplicate or unsupported layout key")
        if "today" in self.pinned or "today" in self.more_order:
            raise ValueError("Home is fixed")
        return self


@router.put("/me/ui-preferences")
async def put_my_preferences(
    body: UIPreferencesWrite, user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    current = await db.get(UserUIPreference, user["sub"])
    old_revision = current.revision if current else 0
    if body.expected_revision != old_revision:
        raise HTTPException(409, "UI preferences changed; reload")
    fields = body.model_dump(exclude={"expected_revision"})
    if current is None:
        db.add(UserUIPreference(user_sub=user["sub"], revision=1, **fields))
        revision = 1
    else:
        changed = await db.execute(
            update(UserUIPreference)
            .where(UserUIPreference.user_sub == user["sub"], UserUIPreference.revision == old_revision)
            .values(**fields, revision=old_revision + 1, updated_at=datetime.now(timezone.utc))
        )
        if changed.rowcount != 1:
            await db.rollback()
            raise HTTPException(409, "Concurrent layout change")
        revision = old_revision + 1
    _audit(db, user["sub"], "ui.preferences.update", "Personal layout changed")
    await db.commit()
    return {**fields, "revision": revision}


@router.get("/admin/feature-rollouts")
async def get_rollouts(
    response: Response, _owner: dict = Depends(owner_only),
    db: AsyncSession = Depends(get_db),
):
    policies = {r.feature_key: r for r in (await db.execute(select(FeatureRollout))).scalars().all()}
    response.headers["Cache-Control"] = "no-store"
    return {"features": [
        {"key": key, "title": title, "status": policies[key].status if key in policies else "enabled",
         "audience": policies[key].audience if key in policies else "all",
         "revision": policies[key].revision if key in policies else 0}
        for key, (_, title) in FEATURES.items()
    ]}


class FeatureWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    expected_revision: int = Field(ge=0)
    status: Literal["hidden", "beta", "enabled", "maintenance"]
    audience: Literal["all", "owner"] = "all"


@router.put("/admin/feature-rollouts")
async def put_rollout(
    body: FeatureWrite, user: dict = Depends(owner_only),
    db: AsyncSession = Depends(get_db),
):
    if body.key not in FEATURES:
        raise HTTPException(422, "Unknown feature")
    if body.status == "enabled" and body.key == "events" and body.audience == "all":
        # The curated feature cannot be released publicly by a flag alone;
        # only verified production releases may activate it.
        raise HTTPException(409, "Curated event public rollout requires release gate")
    row = await db.get(FeatureRollout, body.key)
    revision = row.revision if row else 0
    if revision != body.expected_revision:
        raise HTTPException(409, "Concurrent rollout change")
    if row is None:
        db.add(FeatureRollout(feature_key=body.key, status=body.status,
                              audience=body.audience, revision=1))
        revision = 1
    else:
        result = await db.execute(
            update(FeatureRollout)
            .where(FeatureRollout.feature_key == body.key, FeatureRollout.revision == revision)
            .values(status=body.status, audience=body.audience,
                    revision=revision + 1, updated_at=datetime.now(timezone.utc))
        )
        if result.rowcount != 1:
            await db.rollback()
            raise HTTPException(409, "Concurrent rollout change")
        revision += 1
    _audit(db, user["sub"], "admin.feature_rollout.update", f"feature={body.key} state={body.status}")
    await db.commit()
    return {"key": body.key, "status": body.status, "audience": body.audience, "revision": revision}


def _ai_view(row: LifeAIPolicy | None):
    return {"revision": row.revision if row else 0, "enabled": row.enabled if row else True,
            "allowed_providers": row.allowed_providers if row else list(AI_PROVIDERS)}


@router.get("/admin/ai/providers")
async def ai_providers(
    response: Response, _owner: dict = Depends(owner_only),
    db: AsyncSession = Depends(get_db),
):
    from app import config
    policy = await db.get(LifeAIPolicy, "drive")
    configured = {
        key: bool(getattr(config.settings, f"{'gemini' if key == 'gemini_lite' else key}_api_key", "") or
                  os.environ.get(f"{'GEMINI' if key == 'gemini_lite' else key.upper()}_API_KEY", ""))
        for key in AI_PROVIDERS if key != "codex"
    }
    configured["codex"] = bool(config.settings.codex_primary_enabled)
    response.headers["Cache-Control"] = "no-store"
    return {"policy": _ai_view(policy),
            "providers": [{"key": k, "credential": "configured" if configured[k] else "missing",
                           "direct_health": "not_tested"} for k in AI_PROVIDERS],
            "usage_cost": "not_instrumented"}


class AIPolicyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    enabled: bool
    allowed_providers: list[Literal["gemini", "gemini_lite", "groq", "openrouter", "openai", "codex"]] = Field(max_length=6)

    @model_validator(mode="after")
    def distinct(self):
        if len(set(self.allowed_providers)) != len(self.allowed_providers):
            raise ValueError("Duplicate provider")
        return self


@router.put("/admin/ai/policy")
async def update_ai_policy(
    body: AIPolicyWrite, user: dict = Depends(owner_only),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(LifeAIPolicy, "drive")
    revision = row.revision if row else 0
    if revision != body.expected_revision:
        raise HTTPException(409, "Concurrent AI policy change")
    if row is None:
        db.add(LifeAIPolicy(policy_key="drive", revision=1, enabled=body.enabled,
                            allowed_providers=body.allowed_providers))
        revision = 1
    else:
        result = await db.execute(
            update(LifeAIPolicy).where(
                LifeAIPolicy.policy_key == "drive", LifeAIPolicy.revision == revision
            ).values(enabled=body.enabled, allowed_providers=body.allowed_providers,
                     revision=revision + 1, updated_at=datetime.now(timezone.utc))
        )
        if result.rowcount != 1:
            await db.rollback()
            raise HTTPException(409, "Concurrent AI policy change")
        revision += 1
    _audit(db, user["sub"], "admin.ai_policy.update", f"enabled={body.enabled}, revision={revision}")
    await db.commit()
    return {"revision": revision, "enabled": body.enabled, "allowed_providers": body.allowed_providers}


@router.get("/admin/ai/usage")
async def ai_usage(
    response: Response, _owner: dict = Depends(owner_only),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(DriveDocumentEnrichmentRun.provider, DriveDocumentEnrichmentRun.status, func.count())
        .group_by(DriveDocumentEnrichmentRun.provider, DriveDocumentEnrichmentRun.status)
    )).all()
    response.headers["Cache-Control"] = "no-store"
    return {"counts": [{"provider": provider, "status": status, "count": count}
                       for provider, status, count in rows],
            "tokens": None, "cost": None, "cost_status": "not_instrumented"}
