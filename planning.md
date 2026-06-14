# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This item takes in the name, size and the maximum price of an item the user is looking for, to return a "new item" the user can buy to make an outfit with their wardrobe 
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): what type of clothing piece the item is and what visual features the user wants
- `size` (str): ... The size of the item the user wants
- `max_price` (float): ... The maximum price the user wants to pay for the item

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
Returns the new item found from the listings, with the id, title, description, style_tags and colors to make it easier to create an outfit with other pieces
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the function fails, Recommend similar items to what the user was looking for, if the user declines the item. Prompt the user to enter a different item they would like
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This function takes the new item found by search_listings and finds the peices from the users wardrobe to make a complete outfit (tops, bottoms, outerwear, shoes, accessories)
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ... The new item found which includes the id, title, description, style_tags and colors to make it easier to create an outfit with other pieces
- `wardrobe` (dict): ... The whole users wardrobe which includes tops, bottoms, outerwear, shoes, accessories which each item has their own id, title, description, style_tags and colors, to match to the new item

**What it returns:**
<!-- Describe the return value -->
The function returns a suggested outfit with a short description of each item, so the user can visualize the outfit
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the function fails, recommend the user to find the missing items from the outfit in the listings, call search_listings function for items to complete the outfit
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
The function creates a description for the outfit put together by the suggest_outfit function to post as an caption in instagram, casual and informative.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ... The outfit put together by suggest_outfit, used to see the attributes of each item to make description

**What it returns:**
<!-- Describe the return value -->
a short caption describing the new outfit
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the function fails, tell the user what item is missing to complete the outfit, and run the search listing function to find the missing pieces
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
User inputs what item they want, 
Run Search listings function for item the user inputted,
if item isnt found, prompt the user to input a different item after trying to find similar items
run suggested outfit after a new item is found,
if outfit cannot be generated, tell user items are missing and run search listing function to recommend items for the missing part of the outfit,
run create fit card after a outfit is suggested to generate caption, (failures shouldnt occur in this step),
loop is complete and return new_item with its a attributes, suggested outfit with short description of each piece, caption of outfit it post
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

The agent stores data in different states depending on what tool has been called. First calling the search_listings tool with have the size, description and max price of the new item. The state after that will contain both the new item and wardrobes id, title, description, style_tags and colors, to match to the new item to an outfit created using the users wardrobe. The state after that will include the completed outfit along with a short description of every time to make the create_fit_card generate a caption. The last State is the return where the new item is returned along with a suggested outfit and caption to post.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Recommend a smiliar item, if user rejects then prompt the user to look for a different item |
| suggest_outfit | Wardrobe is empty | alert user of missing items and call search listings function to look for items with similar attributes of the new item |
| create_fit_card | Outfit input is missing or incomplete | Loop wont reach create_fit_card tool if the outfit is incomplete or missing in the suggest_outfit tool |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
                    ┌─────────────────────────────────────┐
                    │  USER INPUT                          │
                    │  description, size, max_price        │
                    └───────────────────┬─────────────────┘
                                        │
                                        v
                    ┌─────────────────────────────────────┐
              ┌────>│  search_listings                     │
              │     └───────────────────┬─────────────────┘
              │                         │
              │                  Item found?
              │              ┌──────────┴──────────┐
              │             NO                     YES
              │              │                      │
              │              v                      │
              │   ┌────────────────────┐            │
              │   │ Recommend similar  │            │
              │   │ items              │            │
              │   └─────────┬──────────┘            │
              │             │                       │
              │      User accepts?                  │
              │       ┌─────┴─────┐                 │
              │      NO          YES                │
              │       │           └────────┐        │
              │       v                     │       │
              │  ┌──────────────┐           │       │
              └──┤ Prompt for   │           │       │
                 │ diff. item   │           v       v
                 └──────────────┘     ┌─────────────────────────┐
                            ┌────────>│  suggest_outfit         │
                            │         │  new_item + wardrobe    │
                            │         └───────────┬─────────────┘
                            │                     │
                            │            Complete outfit?
                            │          ┌──────────┴──────────┐
                            │         NO                     YES
                            │          │                      │
                            │          v                      │
                            │  ┌──────────────────┐           │
                            │  │ Tell user which  │           │
                            │  │ items missing    │           │
                            │  └────────┬─────────┘           │
                            │           │                     │
                            │           v                     │
                            │  ┌──────────────────┐           │
                            └──┤ search_listings  │           │
                               │ for missing      │           │
                               │ pieces           │           │
                               └──────────────────┘           │
                                                               v
                                              ┌─────────────────────────┐
                                              │  create_fit_card        │
                                              │  generate caption       │
                                              └───────────┬─────────────┘
                                                          │
                                                          v
                                              ┌─────────────────────────┐
                                              │  DONE — return:          │
                                              │  • new_item + attributes │
                                              │  • outfit + descriptions │
                                              │  • Instagram caption     │
                                              └─────────────────────────┘
```

State / Session carries data between tools: `search_listings` produces `new_item`,
which `suggest_outfit` combines with the user's `wardrobe` to build `outfit`, which
`create_fit_card` turns into the final caption. The two back-edges are the error paths —
a declined/missing item loops back to `search_listings`, and an incomplete outfit loops
through `search_listings` for the missing pieces before retrying `suggest_outfit`.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For milestone 3 , Claude will be my go to AI Tool. The input I will be providing is the Tools section of planning.md which includes the search_listings, suggest_outfit and the create_fit_card tools. This will give claude the exact context, variables and expectations of each indvivdual tool and how they interact with eachother. I expect three tools that work in returning a new item for the user to buy, a suggested outfit based around the new item and a caption highlighting the outfit and new piece. Ill verify the outputs by choosing certain items in the listings to see if the search_listings returns the items im pointing it too, suggest_outfit will be verified if it makes an outfit with similar attributes to the new item, create_fit_card will be veriffied if its caption includes and accurately describes the items from suggest_outfit.
**Milestone 4 — Planning loop and state management:**
For Milestone 4, Claude will be my go to AI Tool. The Input for the planning loop and state management will be the planning loop and architecture section from planning.md . I expect claude to produce a loop that will run all three tools with error catching that starts certain loops in the case some clothing is missing or needed to fully complete an outfit. Ill verify the output by seeing if the loops does end and called all three tools or if its an infinite loop.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
First the agent will call the search listings tool which inputs the description/name, size and max price of the item the user wants and the tool searches through the listing of items. It Returns an item that matches the users requirements along with is attributes to be used in the generate outfit tool. If the tool cant find an item that matches the users input, then it will recommend items that are close enough to the original item. If the user does not accept, then the user will be prompted to start searching a different item.
**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
After, the new item is put into the suggest_outfit function which has the new_item and and the users wardrobe as parameters. This is to pair the new item with suggested items already owned by the user. If an outfit cannot be generated with items from the wardrobe, then the user will be alerted about the missing items and the search listings tool will be called to search for the missing item with similar attributes as the new item.
**Step 3:**
<!-- Continue until the full interaction is complete -->
Next, the function create fit card is called with the suggested outfit and the new item to create a description of the outfit to post to instagram in a caption
**Final output to user:**
<!-- What does the user actually see at the end? -->
The User sees the new item, a suggested outfit and a caption to post on instagram of the suggested outfit highlighting the new item.