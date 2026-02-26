---
name: interface-design
description: Principle-based interface design with craft, memory, and consistency. Builds dashboards, admin panels, SaaS apps, tools, and data interfaces with intentional design decisions. Saves design systems to .interface-design/system.md for cross-session consistency. Use when building UI, designing components, creating layouts, styling interfaces, or when the user mentions interface design, dashboard design, or UI consistency.
---

# Interface Design

Build interface design with craft and consistency.

**Use for:** Dashboards, admin panels, SaaS apps, tools, settings pages, data interfaces.
**Not for:** Landing pages, marketing sites, campaigns.

---

## The Problem

Without structure, design decisions drift across sessions. Button heights wander (36px, 38px, 40px...), spacing becomes random, and consistency breaks down. This skill enforces intentional, principle-based design with memory.

---

## Where Defaults Hide

Defaults disguise themselves as infrastructure:

- **Typography feels like a container** but it IS your design. Weight, personality, texture shape how the product feels before anyone reads a word.
- **Navigation feels like scaffolding** but it IS your product. Where you are, where you can go, what matters most.
- **Data feels like presentation** but a number on screen is not design. What does this number mean to the person looking at it?
- **Token names feel like implementation** but `--ink` and `--parchment` evoke a world; `--gray-700` evokes a template.

Everything is design. The moment you stop asking "why this?" is when defaults take over.

---

## Intent First

Before touching code, answer these explicitly:

**Who is this human?** Not "users." The actual person — where they are, what's on their mind, what they did 5 minutes ago.

**What must they accomplish?** The verb. Grade submissions. Find the broken deployment. Approve the payment.

**What should this feel like?** Not "clean and modern." Warm like a notebook? Cold like a terminal? Dense like a trading floor? Calm like a reading app?

If you cannot answer with specifics, ask the user. Do not guess. Do not default.

### Every Choice Must Be A Choice

For every decision, explain WHY: Why this layout? Why this color temperature? Why this typeface? Why this spacing? If your answer is "it's common" — you haven't chosen, you've defaulted.

**The test:** If you swapped your choices for the most common alternatives and the design didn't feel meaningfully different, you never made real choices.

### Intent Must Be Systemic

If the intent is warm: surfaces, text, borders, accents, typography — all warm. If dense: spacing, type size, information architecture — all dense. Check your output against stated intent. Does every token reinforce it?

---

## Product Domain Exploration

**Do not propose any direction until you produce all four:**

1. **Domain:** Concepts, metaphors, vocabulary from this product's world. Minimum 5.
2. **Color world:** What colors exist naturally in this domain? If this product were a physical space, what would you see? List 5+.
3. **Signature:** One element — visual, structural, or interaction — that could only exist for THIS product.
4. **Defaults:** 3 obvious choices for this interface type. You can't avoid patterns you haven't named.

Your direction must reference all four. The test: remove the product name from your proposal — could someone identify what it's for?

---

## The Mandate

Before showing the user, look at what you made.

Ask: "If they said this lacks craft, what would they mean?" Fix that thing first.

**The Checks:**
- **Swap test:** If you swapped the typeface/layout for defaults, would anyone notice? Those are the places you defaulted.
- **Squint test:** Blur your eyes. Can you perceive hierarchy? Is anything jumping out harshly?
- **Signature test:** Can you point to five elements where your signature appears?
- **Token test:** Read your CSS variables out loud. Do they sound like THIS product?

---

## Craft Foundations

### Subtle Layering

Surfaces stack with whisper-quiet shifts. Higher elevation = slightly lighter (dark mode) or shadow (light mode). Each jump: only a few percentage points of lightness.

**Key decisions:**
- **Sidebars:** Same background as canvas with subtle border — not a different color.
- **Dropdowns:** One level above parent surface.
- **Inputs:** Slightly darker than surroundings (inset feel).

### Infinite Expression

Every pattern has infinite expressions. A metric display could be a hero number, sparkline, gauge, progress bar, or trend badge. Same sidebar + cards has infinite variations in proportion, spacing, and emphasis.

Never produce identical output. Linear's cards don't look like Notion's. Vercel's metrics don't look like Stripe's. Same concepts, infinite expressions.

### Color Lives Somewhere

Every product exists in a world with colors. Before reaching for a palette, spend time in the product's world. Your palette should feel like it came FROM somewhere.

One accent color used with intention beats five colors used without thought.

---

## Before Writing Each Component

**Mandatory checkpoint — state these before every UI component:**

```
Intent: [who is this human, what must they do, how should it feel]
Palette: [colors from exploration — and WHY]
Depth: [borders / shadows / layered — and WHY]
Surfaces: [elevation scale — and WHY this color temperature]
Typography: [typeface — and WHY]
Spacing: [base unit]
```

If you can't explain WHY for each, you're defaulting. Stop and think.

---

## Design Principles

### Token Architecture
Every color traces back to primitives: foreground (text hierarchy), background (surface elevation), border (separation), brand, semantic. No random hex values.

### Text Hierarchy
Four levels: primary, secondary, tertiary, muted. Use all four consistently.

### Border Progression
Scale from default to subtle to strong to strongest. Match intensity to boundary importance.

### Spacing
Pick a base unit, stick to multiples. Micro (icon gaps), component (buttons/cards), section (groups), major (distinct areas).

### Depth
Choose ONE: borders-only, subtle shadows, layered shadows, or surface color shifts. Don't mix.

### Border Radius
Sharper = technical. Rounder = friendly. Build a scale: small (inputs/buttons), medium (cards), large (modals).

### Typography
Build distinct levels. Headlines: heavy weight, tight tracking. Body: comfortable. Labels: medium weight, smaller. Data: monospace with `tabular-nums`.

### Controls
Never use native `<select>` or `<input type="date">` for styled UI. Build custom components.

### Iconography
Icons clarify, not decorate. One icon set throughout. Remove icons that lose no meaning.

### Animation
Fast micro-interactions (~150ms), smooth easing. Avoid spring/bounce in professional interfaces.

### States
Every interactive element: default, hover, active, focus, disabled. Data: loading, empty, error.

### Navigation Context
Screens need grounding. Include navigation, location indicators, user context.

### Dark Mode
Lean on borders (shadows less visible). Desaturate semantic colors. Same hierarchy system, inverted values.

---

## Design Directions

| Direction | Feel | Best For |
|-----------|------|----------|
| Precision & Density | Tight, technical, monochrome | Developer tools, admin dashboards |
| Warmth & Approachability | Generous spacing, soft shadows | Collaborative tools, consumer apps |
| Sophistication & Trust | Cool tones, layered depth | Finance, enterprise B2B |
| Boldness & Clarity | High contrast, dramatic space | Modern dashboards, data-heavy apps |
| Utility & Function | Muted, functional density | GitHub-style tools |
| Data & Analysis | Chart-optimized, numbers-first | Analytics, BI tools |

---

## Avoid

- Harsh borders (if borders are the first thing you see, they're too strong)
- Dramatic surface jumps (elevation changes should be whisper-quiet)
- Inconsistent spacing (clearest sign of no system)
- Mixed depth strategies
- Missing interaction states
- Dramatic drop shadows
- Large radius on small elements
- Pure white cards on colored backgrounds
- Gradients/color for decoration
- Multiple accent colors
- Different hues for different surfaces (same hue, shift lightness)

---

## Workflow

### If Project Has system.md
Read `.interface-design/system.md` and apply. Decisions are made.

### If No system.md
1. Explore domain — produce all four required outputs
2. Propose direction referencing all four
3. Get user confirmation
4. Build with principles
5. Run mandate checks before showing
6. Offer to save

### Suggest + Ask
Lead with exploration and recommendation:
```
Domain: [5+ concepts]
Color world: [5+ colors from domain]
Signature: [one unique element]
Rejecting: [default] → [alternative] for each

Direction: [approach connecting to above]

Does that direction feel right?
```

### Communication
Be invisible. Don't announce modes or narrate process. Jump into work. State suggestions with reasoning.

---

## After Completing a Task

Always offer to save:

> Want me to save these patterns for future sessions?

If yes, write to `.interface-design/system.md`: direction, depth strategy, spacing base, key component patterns.

Add patterns when used 2+ times, reusable, or has specific measurements worth remembering. Don't save one-offs or temporary experiments.

---

## Deep Dives

For detailed reference material:
- [references/principles.md](references/principles.md) — Code examples, specific values, dark mode
- [references/validation.md](references/validation.md) — Memory management, when to update system.md
- [references/critique.md](references/critique.md) — Post-build craft critique protocol
- [references/example.md](references/example.md) — Craft in action with real decisions
- [references/system-template.md](references/system-template.md) — Template for system.md
- [references/system-precision.md](references/system-precision.md) — Example: Precision & Density
- [references/system-warmth.md](references/system-warmth.md) — Example: Warmth & Approachability
