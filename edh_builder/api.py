from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .deck_builder import DeckBuildError, EdhDeckBuilder
from .exporters import to_grouped_markdown, to_plain_text
from .models import BuildRequest
from .repository import CardRepository
from .rules_knowledge import rules_context_for


app = FastAPI(title="EDH Builder Agent", version="0.1.0")


class BuildPayload(BaseModel):
    commander: str
    theme: str = ""
    budget: float | None = None
    power_level: int = Field(default=6, ge=1, le=10)
    allow_infinite: bool = True
    combo_preference: str = "balanced"
    meta_profile: str = "balanced"
    meta_notes: str = ""
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/cards/search")
def search_cards(q: str, limit: int = 20) -> dict:
    cards = CardRepository().search(q, limit)
    return {"cards": [card.__dict__ | {"colors": sorted(card.colors), "color_identity": sorted(card.color_identity)} for card in cards]}


@app.post("/rules/context")
def rules_context(payload: BuildPayload) -> dict:
    commander = CardRepository().get_by_name(payload.commander)
    if not commander:
        raise HTTPException(status_code=400, detail=f"Commander not found: {payload.commander}")
    request = BuildRequest(**payload.model_dump())
    return {"commander": commander.name, "rules_context": rules_context_for(request, commander)}


@app.post("/decks/build")
def build_deck(payload: BuildPayload) -> dict:
    try:
        deck, errors, plan = EdhDeckBuilder().build(BuildRequest(**payload.model_dump()))
    except DeckBuildError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "commander": deck.commander.name,
        "plan": plan,
        "validation_errors": errors,
        "markdown": to_grouped_markdown(deck, errors, plan),
        "decklist": to_plain_text(deck),
    }
