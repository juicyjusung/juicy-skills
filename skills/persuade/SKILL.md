---
name: persuade
description: "Use when the user wants to convince someone, get buy-in, propose a change, argue a position, or write any text whose goal is persuasion. This includes proposals, pitch emails, Slack messages pushing for a decision, budget justifications, pushback on someone else's plan, or strengthening an existing draft to be more compelling. Use this skill whenever the user mentions: proposing, persuading, convincing, arguing, justifying, making a case, getting approval, pushing back, or writing to influence a decision. Also triggers on Korean equivalents: 제안서, 설득, 주장, 논리적으로 정리, 어필, 납득, 반박, 어떻게 얘기하면 좋을까. Even if the user does not explicitly say 'persuade' — if their writing task involves changing someone's mind or driving action, this skill applies."
---

# Persuasive Writing

Turn ideas into persuasive text through conversation. Help the user clarify their claim, build supporting arguments, check logic, and produce a polished draft.

Works for any medium (Slack, email, blog, proposal, report, etc.). The unifying thread is: the text aims to convince someone.

**Language:** Always communicate and write in the user's language. Detect the language from the user's input and use it throughout — questions, drafts, output, everything.

**Conciseness:** Persuasion is about density of reasoning, not volume of text. Match the length to the medium:
- Slack/chat: 1–3 short paragraphs. No headers. Get to the point immediately.
- Email: 3–5 paragraphs. Brief subject line. Scannable structure.
- Proposal/report: Can be longer, but every paragraph must earn its place. Cut filler.

If the user says "short" or "brief" or the medium is inherently short-form, compress aggressively — one strong piece of evidence beats three weak ones.

**Format:** While drafting, write internally in markdown — it's easier to structure. The final format conversion happens at the Output Selection step, where the user picks their delivery method and format. During the drafting and feedback phase, don't worry about format — focus on content. The conversion to plain text (stripping `#`, `**`, etc.) is applied only at the very end when the user chooses a plain-text output option.

## Process Overview

```
User input → Diagnose state → Determine track
                                  ↓
                  ┌───────────────┴───────────────┐
                  │ Fast Track                     │ Deep Track
                  │ (clear claim, short text)      │ (unclear claim, long text)
                  │                                │
                  │ Confirm claim (1 question max)  │ Establish claim (iterative)
                  │ → Generate evidence + rebuttal  │ → Discover evidence
                  │   + draft in one shot           │ → Strengthen with examples
                  │ → User feedback/revise          │ → Counter-arguments
                  │                                │ → Draft → feedback/revise
                  └───────────────┬───────────────┘
                                  ↓
                          Logic self-check (shared)
                                  ↓
                          Output selection → Tone adjustment (optional)
```

## Step 1: Diagnose State

Analyze three things from the user's first input:

| Element | Question |
|---------|----------|
| **Claim clarity** | Is there a claim expressible in one sentence, or just a vague direction? |
| **Evidence on hand** | Has the user already provided reasons or data? |
| **Context** | Is the audience, medium, or background situation specified? |

### Existing Draft

If the user provides a complete text and asks to make it more persuasive, treat it as Clear claim + Present evidence + Present context → **Fast Track**. Restructure and strengthen the existing text using the 3-layer sandwich structure rather than starting from scratch. Preserve the user's original points and phrasing.

### Track Decision

| Claim | Evidence | Context | Track |
|-------|----------|---------|-------|
| Clear | Present | Present | **Fast** — draft immediately |
| Clear | Present | Missing | **Fast** — ask medium/audience once, then draft |
| Clear | Missing | — | **Fast** — AI generates evidence automatically, presents draft |
| Unclear | — | — | **Deep** — start with claim establishment |

The user can override the track at any time:
- "Just do it quickly" / "Keep it simple" → switch to Fast Track
- "Let's go deeper" / "Do this properly" → switch to Deep Track

## Fast Track

Minimize questions. Show results first.

1. **Confirm claim** — If needed, ask one question to pin down the claim, audience, or medium. If everything is clear, skip ahead.
2. **Generate all at once:**
   - 2–3 structured pieces of evidence
   - A concrete example or data point for each
   - 1 anticipated counter-argument + rebuttal
   - Complete draft in 3-layer sandwich structure (see `references/writing-framework.md`)
3. **Feedback loop** — Present the draft. Revise based on user feedback. Repeat until satisfied.
4. → Proceed to Logic Self-Check

## Deep Track

Progressively refine through focused questions. Ask one question at a time.

### 2-1. Establish the Claim

Narrow a vague direction down to a single-sentence claim.

- Ask questions like: "Ultimately, who do you want to convince of what?"
- One question per message
- Arrive at a **one-sentence claim** agreed upon with the user

This sentence becomes the opening and the foundation of the closing.

### 2-2. Discover Evidence

- "Why do you believe this?"
- "Do you have any experience or data that supports this?"
- Focus on drawing out what the user already knows
- Check for conflicts between pieces of evidence immediately
- Target: 2–3 solid pieces of evidence

### 2-3. Strengthen with Examples

- For each piece of evidence, ask "Can you give me an example?"
- If the user feels they lack material, offer web research: "Want me to look up relevant statistics or studies?"
- Web research uses tavily skills (tavily-search, tavily-research); falls back to WebSearch if tavily fails
- Show search results to the user and confirm which ones to include

### 2-4. Counter-Arguments

- AI presents 1–2 anticipated counter-arguments with draft rebuttals for each
- User can revise or request additional counter-arguments

### 2-5. Draft

Write using the 3-layer sandwich structure (see `references/writing-framework.md` for details):

1. **Claim** (top-down) — state the point up front
2. **Evidence + Example + Explanation** repeated — for each piece of evidence, include why it supports the claim
3. **Counter-argument handling** — acknowledge and rebut
4. **Restatement** — close with the claim in a stronger form, earned by the evidence

User feedback → revise → repeat.

## Logic Self-Check

After the draft is complete, automatically run these four checks:

| Check | What to verify | On failure |
|-------|---------------|------------|
| **Direction alignment** | Does each piece of evidence actually support the claim? | Suggest replacing the evidence or strengthening the connecting sentence |
| **Evidence conflict** | Do evidence A and B contradict each other? | Show the conflict to the user and ask them to choose |
| **Example proof value** | Does the example actually prove the evidence? | Suggest a stronger example or data point |
| **Counter-argument coverage** | Are obvious counter-arguments addressed? | Present the missing counter-argument |

Reporting:
- All clear: "Logic check passed." — one line, move on
- Issues found: show each issue with a suggested fix → apply after user confirmation

## Output Selection

Once the draft is finalized, offer delivery and format options together:

```
The text is ready. How would you like it?

1) Print to terminal
2) Save to file (specify path)
3) Copy to clipboard — plain text
4) Copy to clipboard — markdown
```

- Option 1: Output directly to terminal (markdown rendered naturally)
- Option 2: Ask for file path. If the path ends in `.md`, save as markdown; if `.txt` or any other extension, save as plain text.
- Option 3: Strip all markdown formatting (no `#` headers, no `---`, no `**bold**`) → copy via `pbcopy` (macOS) or `xclip` (Linux). Best for pasting into Slack, email clients, or chat.
- Option 4: Keep markdown formatting intact → copy via `pbcopy`/`xclip`. Best for pasting into Notion, GitHub, or other markdown-aware tools.

**Smart defaults:** If the medium was already established (e.g., "Slack message"), pre-select the matching format — but still show the options so the user can override. For example, if the user said "Slack", default-highlight option 3.

## Tone Adjustment

The default tone for initial drafts is **professional but approachable** — clear, confident, not stiff. Adapt naturally to context clues: Slack leans more casual, a board proposal leans more formal. The user can change the tone after the draft is produced:


```
Would you like to adjust the tone?

1) Formal (reports, official proposals)
2) Casual (Slack, team chat)
3) Direct (short and punchy)
4) Keep as is
```

After tone adjustment, offer the output selection again so the user can get the revised version.

## Web Research

- Default: work within the materials the user provides
- On request or when evidence is thin: search using tavily skills
  - `tavily-search` for general search
  - `tavily-research` for in-depth investigation
- Always show search results to the user and confirm what to include before incorporating
- Fall back to WebSearch if tavily fails

## Key Principles

- **One question at a time** — never pile multiple questions into one message
- **Results first** — especially in Fast Track, show the draft before asking more questions
- **Use the user's words** — preserve their vocabulary and phrasing as much as possible
- **Steps are guides** — if the user wants to skip ahead, follow immediately
- **No invented citations** — never fabricate statistics, study names, or source attributions. If you use a data point, it must be something the user provided, something found via web research, or clearly labeled as a general claim ("studies show…" without a specific fake citation). Making up "Forrester 2024 report" or "Stanford study" destroys credibility if the reader checks.
- **Concise by default** — a shorter, tighter text is almost always more persuasive than a longer, padded one. When in doubt, cut.
- **Writing framework reference** — for detailed structure and logic check principles, see `references/writing-framework.md`
