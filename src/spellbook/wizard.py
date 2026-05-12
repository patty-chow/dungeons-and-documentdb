"""Elara the Arcane Librarian -- RAG over the spells collection."""
from __future__ import annotations

from pymongo.database import Database

from src.llm import chat
from src.spellbook.search import search_spells

ELARA_SYSTEM = """You are Elara, the Arcane Librarian of the Athenaeum.

You are scholarly, precise, and a little theatrical. You answer questions
about Dungeons & Dragons spells using ONLY the spells provided to you in the
context block. If none of the provided spells match the question, say so
honestly and suggest the closest alternative from the context.

Style rules:
- Stay in character as Elara.
- Reference spells by name, level, and school of magic.
- Mention whether a spell requires concentration when it is relevant to the
  question.
- Keep responses to 4-8 sentences. When listing multiple spells, use a
  short bulleted list with one line per spell.
- Do not invent spells. Only use what is in the context.
- Never mention you are an AI, that you are doing "vector search," or that
  spells were "retrieved" -- you are simply a librarian who knows her stock.
"""


def _format_spell_context(spells: list[dict]) -> str:
    """Pretty-print the retrieved spells for inclusion in the LLM prompt."""
    if not spells:
        return "(No spells matched the query.)"
    lines: list[str] = []
    for s in spells:
        lvl = "Cantrip" if s["level"] == 0 else f"Level {s['level']}"
        conc = " (concentration)" if s.get("concentration") else ""
        damage = f" | Damage type: {s['damage_type']}" if s.get("damage_type") else ""
        lines.append(
            f"- {s['name']} -- {lvl} {s['school']}{conc}\n"
            f"  Range: {s.get('range', '')} | Duration: {s.get('duration', '')}{damage}\n"
            f"  {s.get('description', '')[:320]}"
        )
    return "\n".join(lines)


def answer(
    db: Database,
    question: str,
    k: int = 5,
    filters: dict | None = None,
) -> tuple[str, list[dict]]:
    """Run the full RAG pipeline.

    Returns ``(answer_text, spells_retrieved)`` so callers can show the user
    which documents were consulted.
    """
    spells = search_spells(db, question, filters=filters, k=k)
    context = _format_spell_context(spells)
    user = (
        "Spells available from the Athenaeum (the ones you have on hand "
        f"for this question):\n{context}\n\n"
        f'The visitor asks: "{question}"\n\n'
        "Answer in character as Elara, using ONLY the spells above."
    )
    reply = chat(system=ELARA_SYSTEM, user=user, max_tokens=500).strip()
    return reply, spells
