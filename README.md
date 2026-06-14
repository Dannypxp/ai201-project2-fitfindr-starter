# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

I built the three tools in `tools.py` and can be tested on their own before the agent wires them together.

### 1. `search_listings`
- **Purpose:** Takes the name, size, and max price of the item the user is looking for and searches the listings to return a "new item" they can buy and build an outfit around.
- **Inputs:**
  - `description` (str) — what type of clothing piece it is and the visual features the user wants
  - `size` (str, optional) — the size the user wants (case-insensitive, so "M" matches "S/M")
  - `max_price` (float, optional) — the most the user wants to pay
- **Output:** a `list[dict]` of matching listings sorted best-match-first. Each listing has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns an empty list `[]` if nothing matches (it never raises).
- **Purpose in the loop:** the first result becomes the "new item" everything else is built around.

### 2. `suggest_outfit`
- **Purpose:** Takes the new item found by `search_listings` and finds pieces from the user's wardrobe to make a complete outfit (tops, bottoms, outerwear, shoes, accessories).
- **Inputs:**
  - `new_item` (dict) — the new item found, including its id, title, description, style_tags, and colors so it's easy to match
  - `wardrobe` (dict) — the user's whole wardrobe (each item has its own id, name, category, style_tags, colors)
- **Output:** a non-empty `str` describing a suggested outfit with a short description of each item, so the user can picture the look.

### 3. `create_fit_card`
- **Purpose:** Takes the outfit put together by `suggest_outfit` and writes a caption to post on Instagram — casual and informative.
- **Inputs:**
  - `outfit` (str) — the outfit suggestion from `suggest_outfit`
  - `new_item` (dict) — the new item, used to pull in its name, price, and platform for the caption
- **Output:** a short `str` caption describing the new outfit (2–4 sentences, OOTD style).

## Planning Loop

The planning loop lives in `run_agent()` in `agent.py` and follows exactly what I drew in the architecture diagram in `planning.md`:

1. The user inputs what item they want.
2. I parse the query into a description, size, and max price, then run `search_listings` on it.
3. If the item isn't found (empty list), the agent stops and tells the user to try different keywords, a bigger budget, or another size — it does **not** move on to `suggest_outfit` with empty input.
4. Once a new item is found, I take the top result and run `suggest_outfit` to pair it with the wardrobe.
5. After an outfit is suggested, I run `create_fit_card` to generate the caption (this step shouldn't really fail).
6. The loop is done and returns the new item with its attributes, the suggested outfit with a short description of each piece, and the caption to post.

## State Management

The agent stores everything in one session dict that gets built up as each tool runs, so info from one tool gets passed straight into the next:

- First, calling `search_listings` uses the size, description, and max price of the new item the user typed.
- The state after that holds both the new item and the wardrobe, so `suggest_outfit` can match the new item to an outfit made from pieces the user already owns.
- The state after that includes the completed outfit plus a short description of every piece, which is what `create_fit_card` uses to generate the caption.
- The last state is the return, where the new item, the suggested outfit, and the caption all come back together.

There's no re-prompting or hardcoding between steps — the exact item dict that `search_listings` picks is the same object that goes into `suggest_outfit` and `create_fit_card`, and the outfit string `suggest_outfit` returns is the same one `create_fit_card` reads.

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No results match the query | Stops the loop and returns a helpful error message instead of moving on with empty input. |
| `suggest_outfit` | Wardrobe is empty / styling can't run | Falls back to recommending listings the user can buy to build the outfit, instead of crashing. |
| `create_fit_card` | Outfit input is missing or incomplete | Returns a descriptive message telling the user to build a complete outfit first, instead of captioning nothing. |

**Concrete example from my testing:** I ran the no-results query `"designer ballgown size XXS under $5"`. `search_listings` returned `[]`, so the agent set:

```
session["error"]   = "No listings matched 'designer ballgown' in size XXS under $5.
                      Try different keywords, a larger budget, or another size."
session["fit_card"] = None
```

I confirmed it never called `suggest_outfit` or `create_fit_card` on that empty result — the loop exited early exactly like the "Item found? NO" branch in my diagram.

## Spec Reflection

Writing out the vision in planning.md made iplementing the overall project 100% easier because pointing claude to the section I wanted to implement was smooth sailing. This also gave it context on how to connect the multiple tools in the way I wanted.

## AI Usage

Two specific instances in which I used AI to generate sections in this project are iplementing the architecure/loop and the error handling for the three tools. Firstly, was the error handling in which I had to specifically tell claude to stick to my original plan and follow the architecture diagram because it added its own path where it would fall back to general styling advice if the suggest outfit tool failed, I advised it too recommend clothing that is close to the original search and then call the search_listings tool again. The second instance is when the planning loop was writtin in planning.md and used to implement the Loop to run and connect all three tools to work in this project. Claude originally added a outfit guard to the create fit card tool which I didnt want because the diagram wouldnt  have allowed the loop to reach that point if there wasnt a full outfit ready in the last step.


