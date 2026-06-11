# MTG / Commander Rules Knowledge for Deckbuilding Agents

Sources to consult when this file conflicts with current rules:
- Magic Comprehensive Rules: https://magic.wizards.com/en/rules
- Wizards Commander format page: https://magic.wizards.com/en/formats/commander
- Commander Rules Committee rules page: https://mtgcommander.net/index.php/rules/
- Scryfall card/ruling data: https://scryfall.com/docs/api

This document is a deckbuilding-oriented rules summary for LLM planning. It is not a judge document. When exact tournament precision matters, consult the current Comprehensive Rules and card-specific Oracle rulings.

## Commander / EDH Deck Construction

- A normal Commander deck has exactly 100 cards including commander card(s).
- Except for basic lands and cards that explicitly override deck construction limits, the deck is singleton by English card name.
- Every card in the deck must be legal in Commander and must obey the commander's color identity.
- Color identity is not the same as color. It includes mana symbols in mana costs and rules text, plus color indicators and characteristic-defining abilities that define color identity.
- Reminder text does not determine color identity.
- Hybrid and Phyrexian mana symbols count as all colors shown in those symbols for color identity.
- Extort reminder text does not add white/black color identity by itself.
- Double-faced cards and split/adventure-style cards must be evaluated using the full Oracle identity of the card.
- Partner, Background, Doctor's companion, and "can be your commander" effects are special commander permissions. Do not assume every legendary permanent can be a commander unless rules or Oracle text allow it.

## Commander Game Context

- Multiplayer Commander usually rewards repeatable value, efficient interaction, mana development, and resilient win conditions.
- A deckbuilding agent should separate legal construction from power optimization. Legal does not mean good.
- For budget decks, protect the total budget. Do not spend too much of the budget on a single staple unless the user explicitly asks.

## Casting Spells, Free Casting, and Copies

- A spell is cast when the player follows the casting process: move it to the stack, choose modes/targets, determine and pay costs, then it becomes cast.
- Effects that say "you may cast" a card without paying its mana cost still involve casting the spell. They can trigger "whenever you cast" abilities.
- If an effect lets you cast a spell without paying its mana cost, X in the mana cost is normally 0 unless the effect explicitly lets you pay or choose another value.
- Alternative costs generally cannot be combined with another alternative cost. Additional costs may still be paid if applicable.
- A copy of a spell is normally created directly on the stack and is not cast unless the effect explicitly says you may cast the copy.
- Copying a card and casting the copy is different from copying a spell already on the stack. For combo analysis, check the exact wording.

## Cascade

- Cascade triggers when a spell with cascade is cast.
- Cascade exiles cards from the top of the library until a nonland card with lesser mana value than the spell with cascade is exiled.
- The player may cast that exiled card without paying its mana cost.
- The rest of the exiled cards are put on the bottom of the library in a random order.
- Multiple instances of cascade trigger separately.
- The cascaded-into spell is cast during the resolution of the cascade trigger, so it can trigger "whenever you cast" abilities.
- Cascade compares mana value, not the amount of mana actually paid. Delve, convoke, affinity, cost reduction, and alternate costs do not change mana value.
- For split cards and modal double-faced cards, use current Comprehensive Rules/Oracle behavior for mana value. Do not invent shortcuts.
- If the exiled card has X in its mana cost and is cast without paying its mana cost, X is normally 0.
- Deckbuilding implication: cascade decks often want high-impact lower-mana hits and should avoid low-impact cheap cards that dilute cascade outcomes.

## Quandrix, the Proof Notes

- Quandrix, the Proof gives instant and sorcery spells cast from hand cascade.
- Only instant and sorcery spells cast from hand get cascade from this ability.
- Spells cast from exile, graveyard, command zone, or copied on the stack do not get cascade from this ability unless another effect gives it to them.
- The spell's mana value determines the cascade threshold even if the player paid less due to delve, cost reduction, or alternate costs.
- Delve spells such as Treasure Cruise and Dig Through Time are strong with cascade because their mana value is high even when their paid cost is reduced.
- Low-impact one-mana cantrips can be good in normal decks, but in cascade decks they may become poor cascade hits. Balance early setup against cascade quality.

## Combo Validation Principles

- A combo package should include: components, setup requirements, loop condition, payoff, protection, and how it fails.
- Infinite mana is not a win by itself unless the deck has a payoff such as Blue Sun's Zenith, Walking Ballista, Finale of Devastation, Thrasios-style activated abilities, or another outlet.
- Infinite storm count needs a payoff such as Brain Freeze, Aetherflux Reservoir, Grapeshot in legal colors, or another storm/magecraft payoff.
- Infinite untaps require permanents that produce more resources than the loop costs.
- If a combo relies on nonland mana sources, verify those sources produce enough mana after paying activation costs.
- If a combo requires a creature to tap, check summoning sickness unless the creature has haste or has been under its controller's control since the start of their turn.
- If a combo uses a creature's activated ability with tap in the cost, the creature generally cannot activate it the turn it enters without haste.
- If a combo uses a copied spell, verify whether the copy is cast. Many cast triggers only care about actual casting.
- If a combo requires cards in graveyard/exile/hand/battlefield, state those zones explicitly.

## Common EDH Interaction Categories

- Spot removal: answers one problematic permanent or spell.
- Board wipe: resets many creatures/permanents. Do not classify graveyard hate or protection spells as wipes just because they say "each" or "all".
- Protection: protects commander, combo, or board from removal/countermagic.
- Tutors: find combo pieces or key engines. Land ramp is not the same as a general-purpose tutor.
- Graveyard hate: targets graveyard strategies; do not count it as draw or wipe unless it actually performs those roles well.
- Stack interaction: counterspells and effects that stop combos before they resolve.

## Meta-Aware Deckbuilding

- Creature-heavy meta: increase cheap removal and real board wipes.
- Combo-heavy meta: increase cheap interaction, stack interaction, hand/tutor disruption where legal, and faster clocks or compact combos.
- Control-heavy meta: increase card advantage, must-answer engines, instant-speed play, protection, and uncounterable/recursive threats when available.
- Graveyard meta: include graveyard hate, but do not overload if it weakens the deck's main plan.
- Artifact/enchantment meta: prioritize flexible removal that hits artifacts and enchantments.
- Stax meta: prioritize cheap ramp, low curve, flexible permanent removal, and win conditions that do not require overcommitting.

## LLM Guardrails

- Do not claim a deck is legal without checking the deterministic rule validator.
- Do not assume a combo works only because Commander Spellbook lists a related variant; verify zones, costs, summoning sickness, mana production, and payoff.
- Do not include off-color cards even if they are thematically perfect.
- Do not include banned Commander cards.
- Do not use silver-border/acorn/digital-only cards unless the user explicitly allows them.
- Explain uncertainty and call out rules-sensitive assumptions.
