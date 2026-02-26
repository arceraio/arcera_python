# Core Craft Principles

These apply regardless of design direction. This is the quality floor.

---

## Surface & Token Architecture

Professional interfaces build systems, not random color picks.

### The Primitive Foundation

Every color traces back to:

- **Foreground** — text colors (primary, secondary, muted)
- **Background** — surface colors (base, elevated, overlay)
- **Border** — edge colors (default, subtle, strong)
- **Brand** — primary accent
- **Semantic** — functional colors (destructive, warning, success)

Don't invent new colors. Map everything to these primitives.

### Surface Elevation Hierarchy

```
Level 0: Base background (app canvas)
Level 1: Cards, panels (same visual plane as base)
Level 2: Dropdowns, popovers (floating above)
Level 3: Nested dropdowns, stacked overlays
Level 4: Highest elevation (rare)
```

In dark mode, higher = slightly lighter. In light mode, higher = lighter or uses shadow.

### The Subtlety Principle

Study Vercel, Supabase, Linear — surfaces **barely different** but distinguishable. Borders **light but not invisible**.

**Surfaces:** Difference between levels should be a few percentage points of lightness. In dark mode: surface-100 ~7% lighter, surface-200 ~9%, surface-300 ~12%.

**Borders:** Low opacity (0.05-0.12 alpha dark mode, slightly higher light). Should disappear when not looking, findable when needed.

**The squint test:** Blur your eyes. Perceive hierarchy but no single border or surface jumps out.

**Common mistakes:**
- Borders too visible (1px solid gray instead of subtle rgba)
- Dramatic surface jumps
- Different hues for different surfaces
- Harsh dividers where subtle borders would do

### Text Hierarchy via Tokens

Four levels:
- **Primary** — default text, highest contrast
- **Secondary** — supporting text, slightly muted
- **Tertiary** — metadata, timestamps
- **Muted** — disabled, placeholder, lowest contrast

### Border Progression

- **Default** — standard borders
- **Subtle/Muted** — softer separation
- **Strong** — emphasis, hover
- **Stronger** — maximum emphasis, focus rings

### Dedicated Control Tokens

Separate tokens for form controls:
- **Control background** — often different from surfaces
- **Control border** — needs to feel interactive
- **Control focus** — clear focus indication

### Alternative Backgrounds for Depth

Beyond shadows, contrasting backgrounds create depth. An "inset" background makes content feel recessed. Useful for empty states, code blocks, inset panels, visual grouping without borders.

---

## Spacing System

Pick base unit (4px or 8px), use multiples throughout:
- Micro spacing (icon gaps, tight pairs)
- Component spacing (within buttons, inputs, cards)
- Section spacing (between related groups)
- Major separation (between distinct sections)

## Symmetrical Padding

```css
/* Good */
padding: 16px;
padding: 12px 16px;

/* Bad */
padding: 24px 16px 12px 16px;
```

## Border Radius Consistency

System: small (inputs/buttons), medium (cards), large (modals/containers). Don't mix sharp and soft randomly.

## Depth & Elevation Strategy

Choose ONE:

**Borders-only:**
```css
--border: rgba(0, 0, 0, 0.08);
--border-subtle: rgba(0, 0, 0, 0.05);
border: 0.5px solid var(--border);
```

**Single shadow:**
```css
--shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
```

**Layered shadow:**
```css
--shadow-layered:
  0 0 0 0.5px rgba(0, 0, 0, 0.05),
  0 1px 2px rgba(0, 0, 0, 0.04),
  0 2px 4px rgba(0, 0, 0, 0.03),
  0 4px 8px rgba(0, 0, 0, 0.02);
```

## Card Layouts

Design each card's internal structure for its content — but keep surface treatment consistent: same border weight, shadow depth, corner radius, padding scale.

## Isolated Controls

Never use native form elements for styled UI. Build custom:
- Custom select: trigger button + positioned dropdown
- Custom date picker: input + calendar popover
- Custom checkbox/radio: styled div with state management

Custom select triggers: `display: inline-flex` with `white-space: nowrap`.

## Typography Hierarchy

- **Headlines** — heavier weight, tighter letter-spacing
- **Body** — comfortable weight for readability
- **Labels/UI** — medium weight, smaller sizes
- **Data** — monospace, `tabular-nums` for alignment

## Monospace for Data

Numbers, IDs, codes, timestamps in monospace with `tabular-nums`.

## Iconography

Icons clarify, not decorate. One set throughout. Standalone icons get subtle background containers.

## Animation

Micro-interactions: ~150ms. Larger transitions: 200-250ms. Deceleration easing (ease-out). No spring/bounce in professional interfaces.

## Contrast Hierarchy

Four levels: foreground → secondary → muted → faint.

## Color Carries Meaning

Gray builds structure. Color communicates status, action, emphasis. Unmotivated color is noise.

## Navigation Context

Include navigation, location indicators, user context. Sidebars: same background as main content, border for separation.

## Dark Mode

- Borders over shadows
- Desaturate semantic colors
- Same hierarchy, inverted values
