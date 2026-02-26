# Craft in Action

How subtle layering translates to real decisions. Learn the thinking, not the code. Your values will differ — the approach won't.

---

## The Subtle Layering Mindset

**You should barely notice the system working.**

When you look at Vercel's dashboard, you don't think "nice borders." You just understand the structure. The craft is invisible — that's how you know it's working.

---

## Example: Dashboard with Sidebar and Dropdown

### Surface Decisions

Each elevation jump: only a few percentage points of lightness. Barely visible in isolation, but when surfaces stack, hierarchy emerges. Whisper-quiet shifts you feel rather than see.

**What NOT to do:** Dramatic jumps between elevations. Different hues for different levels. Keep same hue, shift only lightness.

### Border Decisions

**Why rgba, not solid colors?** Low opacity borders blend with background. A low-opacity white border on dark surface is barely there — defines edge without demanding attention. Solid hex borders look harsh.

**The test:** From arm's length, if borders are the first thing you notice, reduce opacity. If you can't find where regions end, increase slightly.

### Sidebar Decision

**Why same background as canvas?** Different colors fragment visual space into "sidebar world" and "content world." Same background + subtle border = sidebar is part of the app, not separate. Vercel and Supabase do this.

### Dropdown Decision

**Why one level above parent?** If both share same level, dropdown blends into card and layering is lost. Slightly higher surface feels "above" without being dramatic.

---

## Example: Form Controls

### Input Background

**Why darker, not lighter?** Inputs are "inset" — they receive content. Slightly darker background signals "type here" without heavy borders.

### Focus State

**Why subtle?** Noticeable increase in border opacity is enough. Subtle-but-noticeable — same principle as surfaces.

---

## Adapt to Context

Your product might need warmer hues, cooler hues, different lightness progression, or light mode (higher elevation = shadow, not lightness).

**The principle is constant:** barely different, still distinguishable. Values adapt to context.

---

## The Craft Check

1. Blur your eyes or step back
2. Can you still perceive hierarchy?
3. Is anything jumping out?
4. Can you tell where regions begin and end?

If hierarchy is visible and nothing is harsh — subtle layering is working.
