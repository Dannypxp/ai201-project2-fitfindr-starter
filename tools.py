"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

# Common words to ignore when scoring keyword overlap — they carry no signal
# about what kind of item the user wants.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "with", "for", "of", "to", "in", "on",
    "my", "i", "im", "looking", "want", "wanted", "need", "some", "any",
    "that", "this", "it", "is", "are", "size", "under", "below", "cheap",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase `text` and split into a set of meaningful word tokens."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


# ── Groq client ───────────────────────────────────────────────────────────────

# Default Groq model used by the LLM-backed tools.
_MODEL = "llama-3.3-70b-versatile"


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _format_item(item: dict) -> str:
    """Render a listing or wardrobe item as a compact one-line description."""
    colors = ", ".join(item.get("colors", []))
    tags = ", ".join(item.get("style_tags", []))
    # Listings use 'title'; wardrobe items use 'name'.
    label = item.get("title") or item.get("name", "item")
    parts = [label]
    if item.get("category"):
        parts.append(f"({item['category']})")
    if colors:
        parts.append(f"colors: {colors}")
    if tags:
        parts.append(f"style: {tags}")
    return " — ".join(parts)


# Categories needed for a complete, wearable outfit. Outerwear and accessories
# are treated as optional extras, not gaps that block the look.
_REQUIRED_CATEGORIES = ["tops", "bottoms", "shoes"]


def _outfit_gaps(new_item: dict, items: list[dict]) -> list[str]:
    """
    Return the required categories not covered by the new item or the wardrobe.

    These are the pieces the user would still need to complete an outfit.
    """
    have = {str(new_item.get("category", "")).lower()}
    have |= {str(i.get("category", "")).lower() for i in items}
    return [c for c in _REQUIRED_CATEGORIES if c not in have]


def _recommend_for_gaps(new_item: dict, gaps: list[str]) -> str:
    """
    For each missing category, search the listings for an item that matches the
    new item's vibe and build a recommendation block the user can act on.

    Returns an empty string if there are no gaps or nothing suitable is found.
    """
    if not gaps:
        return ""

    style = " ".join(new_item.get("style_tags", []))
    lines = []
    for category in gaps:
        # Bias the search toward the new item's style so the gap-filler matches,
        # but only keep listings that are actually in the missing category —
        # keyword scoring alone can rank an off-category item higher.
        matches = [
            m for m in search_listings(f"{category} {style}".strip())
            if str(m.get("category", "")).lower() == category
        ]
        if matches:
            pick = matches[0]
            lines.append(
                f"  - {category.capitalize()}: {pick['title']} "
                f"(${pick['price']:.0f} on {pick.get('platform', 'a listing')})"
            )
        else:
            lines.append(f"  - {category.capitalize()}: no match in listings yet")

    if not lines:
        return ""

    header = (
        "\n\nTo complete the outfit, you'll want to add "
        f"{', '.join(gaps)}. Here are pieces from the listings to fill the gaps:\n"
    )
    return header + "\n".join(lines)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query_tokens = _tokenize(description)

    scored: list[tuple[int, dict]] = []
    for item in listings:
        # 1. Price filter (inclusive).
        if max_price is not None and item["price"] > max_price:
            continue

        # 2. Size filter — case-insensitive substring so "M" matches "S/M".
        if size:
            if size.strip().lower() not in str(item.get("size", "")).lower():
                continue

        # 3. Score by keyword overlap with the description.
        item_tokens = _tokenize(item["title"]) | _tokenize(item["description"])
        item_tokens |= {t.lower() for t in item.get("style_tags", [])}
        item_tokens |= {c.lower() for c in item.get("colors", [])}
        item_tokens.add(str(item.get("category", "")).lower())
        if item.get("brand"):
            item_tokens |= _tokenize(item["brand"])

        score = len(query_tokens & item_tokens)

        # 4. Drop listings with no keyword overlap.
        if score == 0:
            continue

        scored.append((score, item))

    # 5. Sort by score, highest first, and return the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    new_item_desc = _format_item(new_item)
    items = wardrobe.get("items", []) if wardrobe else []

    # Identify which categories the wardrobe can't cover for this outfit, so we
    # can recommend listings to fill those gaps below.
    gaps = _outfit_gaps(new_item, items)

    if not items:
        # Empty wardrobe → general styling advice instead of failing.
        prompt = (
            f"A shopper is considering this thrifted item:\n  {new_item_desc}\n\n"
            "Their wardrobe is empty, so you can't pair it with anything they own. "
            "Suggest a complete outfit built around this piece by describing the kinds "
            "of items that would pair well (tops, bottoms, outerwear, shoes, "
            "accessories) and the overall vibe. Give a short description of each "
            "suggested piece so they can picture the look and know what to shop for."
        )
    else:
        wardrobe_lines = "\n".join(f"  - {_format_item(i)}" for i in items)
        prompt = (
            f"A shopper is considering this thrifted item:\n  {new_item_desc}\n\n"
            f"Here is everything in their wardrobe:\n{wardrobe_lines}\n\n"
            "Build 1-2 complete outfits around the thrifted item using ONLY pieces "
            "from their wardrobe above (tops, bottoms, outerwear, shoes, accessories). "
            "Refer to each wardrobe piece by name. Give a short description of every "
            "item in the outfit so the shopper can visualize the full look. If a key "
            "category is missing from their wardrobe, say which piece they'd still need."
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are FitFindr, a friendly personal stylist for secondhand "
                        "fashion. You build cohesive outfits and explain why pieces work "
                        "together. Be concise and concrete."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        outfit = response.choices[0].message.content.strip()
    except Exception:
        # Styling step failed — fall back to recommending listings the user can
        # buy to build the outfit themselves, rather than crashing the agent.
        fallback_gaps = gaps or _REQUIRED_CATEGORIES
        recs = _recommend_for_gaps(new_item, fallback_gaps)
        return (
            "I couldn't generate a styled outfit right now, but you can build one "
            f"around the {_format_item(new_item)}." + (recs or "")
        )

    # Outfit generated — if the wardrobe can't cover every required piece,
    # recommend listings to fill the gaps so the user can complete the look.
    return outfit + _recommend_for_gaps(new_item, gaps)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard against an empty / whitespace-only outfit — return a descriptive
    # error message instead of captioning nothing or raising an exception.
    if not outfit or not outfit.strip():
        return (
            "Can't write a caption — no complete outfit was provided. "
            "Build a complete outfit first, then try again."
        )

    # Build a prompt with the item details and the outfit.
    price = new_item.get("price")
    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else "a steal"
    item_name = new_item.get("title") or new_item.get("name", "this piece")
    platform = new_item.get("platform", "secondhand")

    prompt = (
        f"Write a short, shareable caption for an outfit-of-the-day social post.\n\n"
        f"The thrifted star of the outfit:\n"
        f"  - {item_name} ({price_str}, found on {platform})\n\n"
        f"The full outfit:\n{outfit.strip()}\n\n"
        "Guidelines:\n"
        "- 2-4 sentences, casual and authentic — like a real OOTD post, not a "
        "product listing.\n"
        f"- Mention the item name, its price ({price_str}), and the platform "
        f"({platform}) naturally, each only once.\n"
        "- Capture the specific vibe of the outfit.\n"
        "- Sound fresh and human. You can use a couple of tasteful hashtags."
    )

    # Call the LLM (higher temperature for variety) and return the caption.
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write punchy, authentic social media captions for "
                        "secondhand fashion finds. You sound like a real person "
                        "excited about a thrift score, never like an ad."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Never crash the agent on an API error — return a usable fallback caption.
        return (
            f"Thrifted this {item_name} for {price_str} on {platform} and styled a "
            "whole look around it. Secondhand hits different. #thrifted #ootd"
        )
