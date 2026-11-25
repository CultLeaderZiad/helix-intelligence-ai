"""Ask Helix: read-only agent, ad variant drafts, and briefs (approved proposals)."""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import account_rate_limit, get_current_user, get_db, require_feature
from app.core.tenancy import get_user_org_ids
from app.models.user import User
from app.services import agent_conversation_service as conversations, agent_service, billing_service

router = APIRouter(dependencies=[Depends(require_feature("discover"))])
_limit = Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class Reference(BaseModel):
    type: Literal["search", "draft", "board", "monitor", "ad"]
    id: str = Field(min_length=1, max_length=200)


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: List[Turn] = Field(default_factory=list, max_length=12)
    lang: Literal["en", "ar"] = "en"
    # Things the user pointed at with "@": resolved on the server from their own workspace.
    references: List[Reference] = Field(default_factory=list, max_length=5)
    effort: Literal["quick", "think", "deep"] = "think"
    # The one assistant shown in the model picker. Anything else is refused.
    model: Literal["cyreax-z1"] = "cyreax-z1"
    # Continue a saved conversation. The server then uses its own saved turns as memory and
    # ignores `history`. Without it, a new conversation is saved.
    conversation_id: Optional[str] = Field(default=None, max_length=64)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    pinned: Optional[bool] = None
    archived: Optional[bool] = None


class GenerateBody(BaseModel):
    creative_id: str = Field(min_length=1, max_length=100)
    product: str = Field(min_length=10, max_length=500)
    language: Literal["ar", "en"] = "ar"
    dialect: Optional[Literal["egyptian", "gulf", "levantine", "msa"]] = "egyptian"


class BriefBody(BaseModel):
    brand_id: str = Field(min_length=1, max_length=200)


async def _ctx(db: AsyncSession, user: User):
    org = await billing_service.get_or_create_default_org(db, user)
    return org.id, await get_user_org_ids(db, user)


@router.get("/limits")
async def agent_limits(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id, _scope = await _ctx(db, current_user)
    return await agent_service.limits(db, org_id)


@router.get("/mentions")
async def mentions(q: str = Query("", max_length=100), limit: int = Query(20, ge=1, le=40),
                   db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """What the "@" menu offers: the caller's own searches, drafts, boards and monitors."""
    from app.services import agent_mentions

    org_id, scope = await _ctx(db, current_user)
    return {"items": await agent_mentions.candidates(db, current_user, org_id, scope, q, limit)}


@router.post("/ask", dependencies=[_limit])
async def ask(body: AskBody, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id, scope = await _ctx(db, current_user)
    history = [t.model_dump() for t in body.history]
    if body.conversation_id:
        history = await conversations.history_for_model(db, current_user, org_id, body.conversation_id)
    result = await agent_service.ask(db, current_user, org_id, scope, body.question, history, body.lang,
                                     [r.model_dump() for r in body.references], body.effort)
    result["conversation_id"] = await conversations.record_turn(
        db, current_user, org_id, body.conversation_id, body.question, result)
    return result


@router.get("/conversations")
async def list_conversations(archived: bool = Query(False), db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    org_id, _scope = await _ctx(db, current_user)
    return {"items": await conversations.list_conversations(db, current_user, org_id, archived),
            "max_active": conversations.MAX_ACTIVE}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    org_id, _scope = await _ctx(db, current_user)
    return await conversations.get_conversation(db, current_user, org_id, conversation_id)


@router.patch("/conversations/{conversation_id}", dependencies=[_limit])
async def update_conversation(conversation_id: str, body: ConversationUpdate, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    org_id, _scope = await _ctx(db, current_user)
    return await conversations.update_conversation(db, current_user, org_id, conversation_id, title=body.title,
                                                   pinned=body.pinned, archived=body.archived)


@router.delete("/conversations/{conversation_id}", dependencies=[_limit])
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    org_id, _scope = await _ctx(db, current_user)
    return await conversations.delete_conversation(db, current_user, org_id, conversation_id)


@router.post("/generate", dependencies=[_limit])
async def generate(body: GenerateBody, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id, scope = await _ctx(db, current_user)
    return await agent_service.generate_variants(db, current_user, org_id, scope, body.creative_id, body.product,
                                                 body.language, body.dialect)


@router.post("/brief", dependencies=[_limit])
async def brief(body: BriefBody, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id, scope = await _ctx(db, current_user)
    return await agent_service.create_brief(db, current_user, org_id, scope, body.brand_id)
