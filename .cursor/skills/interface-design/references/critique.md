# Critique

Your first build shipped the structure. Now look at it the way a design lead reviews a junior's work — not asking "does this work?" but "would I put my name on this?"

---

## The Gap

There's a distance between correct and crafted. Correct means the layout holds, the grid aligns, the colors don't clash. Crafted means someone cared about every decision down to the last pixel. You can feel the difference — the way you tell a hand-thrown mug from an injection-molded one. Both hold coffee. One has presence.

Your first output lives in correct. This process pulls it toward crafted.

---

## See the Composition

Step back. Look at the whole thing.

Does the layout have rhythm? Great interfaces breathe unevenly — dense tooling areas give way to open content, heavy elements balance against light ones, the eye travels through the page with purpose. Default layouts are monotone: same card size, same gaps, same density everywhere.

Are proportions doing work? A 280px sidebar next to full-width content says "navigation serves content." A 360px sidebar says "these are peers." The specific number declares what matters.

Is there a clear focal point? Every screen has one thing the user came here to do. That thing should dominate — through size, position, contrast, or space around it.

---

## See the Craft

Move close. Pixel-close.

Spacing grid non-negotiable — every value a multiple of 4, no exceptions. But correctness alone isn't craft. A tool panel at 16px padding feels workbench-tight; the same card at 24px feels like a brochure.

Typography should be legible even squinted. If size is the only thing separating headline from body from label, hierarchy is too weak. Weight, tracking, and opacity create layers size alone can't.

Surfaces should whisper hierarchy. Remove every border mentally — can you still perceive structure through surface color alone?

Interactive elements need life. Every button, link, clickable region responds to hover and press. Missing states make an interface feel like a photograph of software.

---

## See the Content

Read every visible string as a user would. Not checking for typos — checking for truth.

Does this screen tell one coherent story? Could a real person at a real company be looking at exactly this data? Content incoherence breaks the illusion faster than any visual flaw.

---

## See the Structure

Open the CSS and find the lies — places that look right but are held together with tape.

Negative margins undoing parent padding. Calc() as workarounds. Absolute positioning to escape layout flow. Each is a shortcut where a clean solution exists.

---

## Again

Look at your output one final time.

Ask: "If they said this lacks craft, what would they point to?"

That thing — fix it. Then ask again.

The first build was the draft. The critique is the design.
