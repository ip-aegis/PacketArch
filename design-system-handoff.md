# Aurora Glass — Design System Handoff

A drop-in spec to replicate the Jarvis UI look-and-feel in another app. Hand this whole document to a coding agent. The agent should be able to bootstrap the same visual vocabulary without ever seeing the Jarvis codebase.

---

## 1. The Idea (read this first)

**Aurora Glass** is a dark-mode-first design system built on three ideas:

1. **A living background.** A fixed full-viewport gradient layer (the "aurora") sits behind everything — multiple radial gradients that drift slowly and shift hue based on time of day. It is the single source of color in the app. Every other surface is muted next to it.
2. **Glass surfaces over the aurora.** Cards, rails, modals are translucent and blurred. The aurora bleeds through them. This produces depth without heavy shadows.
3. **Cyan as the only accent.** A single signature color (`#00bceb`, "Cisco Magnetic" cyan) drives focus rings, active states, primary buttons, and hover glows. Aurora violets/magentas/teals appear only in the background gradient and in occasional gradient text fills.

The three design moves that make it feel premium and not generic AI:

- **The aurora moves.** A 60-second drift animation + time-of-day hue shifts give the page a sense of depth and time. Without this, the app would look like a flat dark theme.
- **Glass blur is real.** `backdrop-filter: blur()` over a colorful background does the heavy lifting. Cards get hairline borders + subtle inner highlight, never heavy drop shadows.
- **Severity is communicated through glow, not fill.** A critical alert is a card with a red box-shadow halo, not a red background. Calmer, more readable, more distinctive.

If you keep these three, the rest is interchangeable.

---

## 2. Stack & Tooling

- **Tailwind CSS v4** (the v4 syntax — `@theme`, `@utility`, `@import "tailwindcss"`)
- **React 19** + Vite (any React framework works — the design system is CSS-driven)
- **`lucide-react`** for icons (sharp, geometric, line-style — matches the aesthetic)
- **`clsx`** for conditional classes
- Fonts: **Inter** (sans, with feature settings `cv11`, `ss01`, `ss03`) and **JetBrains Mono** (mono)

You don't need Recharts/Tiptap/etc. unless you're building those features. The visual system is in one CSS file plus ~10 component patterns.

Install order:
```bash
npm install tailwindcss @tailwindcss/vite clsx lucide-react
# Inter + JetBrains Mono via Google Fonts <link> in index.html, or self-hosted
```

Wire Tailwind in `vite.config.ts`:
```ts
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({ plugins: [tailwindcss(), react()] })
```

---

## 3. The Tokens (paste this whole block into your global CSS)

This is the core of the system. Put it in `src/index.css` (or equivalent) as the very first thing imported. Everything else — components, utilities, hover states — reads from these.

```css
@import "tailwindcss";

@theme {
  /* Cisco Magnetic primary — single accent across the whole app */
  --color-primary-50:  #e6f9ff;
  --color-primary-100: #ccf3ff;
  --color-primary-200: #99e7ff;
  --color-primary-300: #66dbff;
  --color-primary-400: #33cfff;
  --color-primary-500: #00bceb;
  --color-primary:     #00bceb;
  --color-primary-600: #0096bc;
  --color-primary-700: #00718d;
  --color-primary-800: #004b5e;
  --color-primary-900: #00262f;

  /* Aurora accent palette — only appears in background + gradient text fills */
  --color-aurora-violet:  #7c5cff;
  --color-aurora-magenta: #d946ef;
  --color-aurora-teal:    #14e4d4;
  --color-aurora-cobalt:  #3b82f6;
  --color-aurora-rose:    #ff5e93;

  /* Severity — used as glows and borders, rarely as fills */
  --color-success:      #6cc04a;
  --color-success-glow: rgba(108, 192, 74, 0.45);
  --color-warning:      #ffcc00;
  --color-warning-glow: rgba(255, 204, 0, 0.45);
  --color-error:        #cf2030;
  --color-error-glow:   rgba(207, 32, 48, 0.5);
  --color-info-glow:    rgba(0, 188, 235, 0.45);

  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Two radii do everything: 8px for buttons/inputs, 16px for cards/panes */
  --radius-magnetic: 8px;
  --radius-glass:    16px;
  --radius-pill:     9999px;

  --shadow-glow-sm: 0 0 12px rgba(0, 188, 235, 0.18);
  --shadow-glow-md: 0 0 24px rgba(0, 188, 235, 0.25);
  --shadow-glow-lg: 0 0 48px rgba(0, 188, 235, 0.35);
  --shadow-elev-1:  0 1px 2px rgba(0, 0, 0, 0.25), 0 4px 12px rgba(0, 0, 0, 0.2);
  --shadow-elev-2:  0 4px 8px rgba(0, 0, 0, 0.3),  0 12px 32px rgba(0, 0, 0, 0.35);
  --shadow-elev-3:  0 8px 16px rgba(0, 0, 0, 0.35), 0 32px 64px rgba(0, 0, 0, 0.45);
}

/* Surface scale via CSS variables so we can flip dark/light at runtime */
@theme inline {
  --color-surface-50:  rgb(var(--surface-50));
  --color-surface-100: rgb(var(--surface-100));
  --color-surface-200: rgb(var(--surface-200));
  --color-surface-300: rgb(var(--surface-300));
  --color-surface-400: rgb(var(--surface-400));
  --color-surface-500: rgb(var(--surface-500));
  --color-surface-600: rgb(var(--surface-600));
  --color-surface-700: rgb(var(--surface-700));
  --color-surface:     rgb(var(--surface-700));
  --color-surface-800: rgb(var(--surface-800));
  --color-surface-900: rgb(var(--surface-900));
  --color-foreground:  rgb(var(--foreground));
}

:root {
  /* Default = dark mode (prevents flash before JS) */
  --surface-50:  245 245 247;
  --surface-100: 232 232 237;
  --surface-200: 209 209 219;
  --surface-300: 160 160 176;
  --surface-400: 107 107 128;
  --surface-500: 74 74 96;
  --surface-600: 53 53 80;
  --surface-700: 37 37 66;
  --surface-800: 26 26 46;
  --surface-900: 12 12 22;
  --foreground:  255 255 255;

  /* Aurora gradient hue stops — JS shifts these through the day */
  --aurora-h1: 195;   /* primary cyan node */
  --aurora-h2: 260;   /* violet node */
  --aurora-h3: 310;   /* magenta node */
  --aurora-intensity: 0.55;
}

:root.light {
  --surface-50:  15 15 26;
  --surface-100: 26 26 46;
  --surface-200: 53 53 80;
  --surface-300: 107 107 128;
  --surface-400: 140 140 160;
  --surface-500: 180 180 195;
  --surface-600: 218 218 228;
  --surface-700: 255 255 255;
  --surface-800: 245 245 247;
  --surface-900: 255 255 255;
  --foreground:  26 26 46;
  --aurora-intensity: 0.18;
}

/* Time-of-day classes applied to <html> by JS — see Section 5 */
:root.aurora-dawn   { --aurora-h1: 200; --aurora-h2: 230; --aurora-h3: 285; }
:root.aurora-day    { --aurora-h1: 195; --aurora-h2: 215; --aurora-h3: 260; }
:root.aurora-dusk   { --aurora-h1: 195; --aurora-h2: 280; --aurora-h3: 320; }
:root.aurora-night  { --aurora-h1: 200; --aurora-h2: 260; --aurora-h3: 310; }
```

---

## 4. The Aurora Layer (the part that makes it feel alive)

Mount a single `<div class="aurora-canvas" />` once at the app root. Everything else floats above it. The CSS:

```css
html, body, #root { height: 100%; }
body {
  @apply antialiased;
  color: rgb(var(--foreground));
  background: rgb(var(--surface-900));
  font-family: 'Inter', system-ui, sans-serif;
  font-feature-settings: 'cv11', 'ss01', 'ss03';
  overflow: hidden;  /* the main scroll lives inside <main>, see Section 7 */
}

.aurora-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background:
    radial-gradient(ellipse 80% 60% at 15% 20%,
      hsla(var(--aurora-h1), 90%, 55%, calc(var(--aurora-intensity) * 0.6)) 0%, transparent 60%),
    radial-gradient(ellipse 70% 70% at 85% 10%,
      hsla(var(--aurora-h2), 85%, 60%, calc(var(--aurora-intensity) * 0.5)) 0%, transparent 55%),
    radial-gradient(ellipse 90% 60% at 50% 100%,
      hsla(var(--aurora-h3), 80%, 55%, calc(var(--aurora-intensity) * 0.45)) 0%, transparent 65%),
    radial-gradient(ellipse 50% 50% at 90% 80%,
      hsla(var(--aurora-h1), 85%, 50%, calc(var(--aurora-intensity) * 0.35)) 0%, transparent 60%),
    rgb(var(--surface-900));
}

/* The drift animation — this is what makes it feel alive */
.aurora-canvas::before {
  content: '';
  position: absolute;
  inset: -10%;
  background: inherit;
  opacity: 0.7;
  filter: blur(40px);
  animation: aurora-drift 60s ease-in-out infinite alternate;
}

/* Subtle SVG noise to prevent gradient banding */
.aurora-canvas::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.06 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  opacity: 0.5;
  mix-blend-mode: overlay;
  pointer-events: none;
}

@keyframes aurora-drift {
  0%   { transform: translate(0, 0) scale(1);    filter: hue-rotate(0deg) blur(40px); }
  50%  { transform: translate(2%, -1.5%) scale(1.04); filter: hue-rotate(8deg) blur(50px); }
  100% { transform: translate(-1.5%, 1%) scale(0.98); filter: hue-rotate(-6deg) blur(40px); }
}
```

**Don't skip the noise overlay.** Without it, gradients band visibly on most monitors and the whole effect collapses.

---

## 5. Time-of-Day Hue Shifting (mount once)

A small effect that wires aurora hue stops to the wall clock. This is what makes the app feel different at 8am vs. 11pm.

```tsx
// AuroraBackground.tsx — mount once at the app root, above all routes
import { useEffect } from 'react'

export default function AuroraBackground() {
  useEffect(() => {
    const setTimeClass = () => {
      const hour = new Date().getHours()
      const root = document.documentElement
      root.classList.remove('aurora-dawn', 'aurora-day', 'aurora-dusk', 'aurora-night')
      if      (hour >= 5  && hour < 9)  root.classList.add('aurora-dawn')
      else if (hour >= 9  && hour < 17) root.classList.add('aurora-day')
      else if (hour >= 17 && hour < 21) root.classList.add('aurora-dusk')
      else                              root.classList.add('aurora-night')
    }
    setTimeClass()
    const id = window.setInterval(setTimeClass, 30 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [])

  return <div className="aurora-canvas" aria-hidden="true" />
}
```

---

## 6. Glass Utilities (the core surface vocabulary)

Add these as Tailwind v4 `@utility` blocks in the same CSS file. Components compose with these.

```css
/* Default card surface — most cards use this */
@utility glass-pane {
  position: relative;
  background: rgba(37, 37, 66, 0.45);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    var(--shadow-elev-1);
}

/* For modals + anything that needs to read clearly over busy content */
@utility glass-pane-strong {
  background: rgba(26, 26, 46, 0.7);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), var(--shadow-elev-2);
}

/* For low-emphasis grouping — quieter than default */
@utility glass-pane-subtle {
  background: rgba(37, 37, 66, 0.28);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}

/* Floating navigation rail / sticky header */
@utility glass-rail {
  background: rgba(15, 15, 26, 0.55);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: var(--shadow-elev-2), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

/* Pill — for tags, status chips, badges */
@utility glass-pill {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
}

/* Add to any glass-pane that should respond to hover */
@utility glass-interactive {
  transition:
    transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
    border-color 220ms ease-out;
}
.glass-interactive:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 188, 235, 0.35);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    var(--shadow-elev-2),
    0 0 32px rgba(0, 188, 235, 0.15);
}

/* Severity glows — apply to cards/badges that need to broadcast urgency */
@utility glow-critical { box-shadow: 0 0 24px rgba(207, 32, 48, 0.45), inset 0 0 0 1px rgba(207, 32, 48, 0.4); }
@utility glow-warning  { box-shadow: 0 0 22px rgba(255, 204, 0, 0.4),  inset 0 0 0 1px rgba(255, 204, 0, 0.4); }
@utility glow-success  { box-shadow: 0 0 22px rgba(108, 192, 74, 0.4), inset 0 0 0 1px rgba(108, 192, 74, 0.4); }
@utility glow-primary  { box-shadow: 0 0 28px rgba(0, 188, 235, 0.45), inset 0 0 0 1px rgba(0, 188, 235, 0.45); }

/* Gradient text — used sparingly for hero stats / brand wordmarks */
@utility text-gradient-primary {
  background: linear-gradient(135deg, #00bceb 0%, #7c5cff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
@utility text-gradient-aurora {
  background: linear-gradient(120deg, #14e4d4 0%, #00bceb 35%, #7c5cff 70%, #d946ef 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* Hero typography — oversized, ultralight, tabular numerals */
@utility display-hero {
  font-size: clamp(3rem, 8vw, 6rem);
  font-weight: 200;
  letter-spacing: -0.04em;
  line-height: 0.95;
  font-variant-numeric: tabular-nums;
}
@utility display-stat {
  font-size: clamp(1.75rem, 3.5vw, 3rem);
  font-weight: 300;
  letter-spacing: -0.025em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
@utility eyebrow {
  font-size: 0.6875rem;  /* 11px */
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
}
```

---

## 7. Buttons & Inputs

```css
@utility magnetic-button { @apply px-4 py-2 rounded-magnetic font-medium transition-all duration-200; }

@utility magnetic-button-primary {
  @apply magnetic-button text-white;
  background: linear-gradient(180deg, #00cdff 0%, #00a4cd 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 4px 12px rgba(0, 188, 235, 0.25);
}
.magnetic-button-primary:hover {
  background: linear-gradient(180deg, #00d8ff 0%, #00b3df 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 6px 18px rgba(0, 188, 235, 0.4);
  transform: translateY(-1px);
}

@utility magnetic-button-secondary {
  @apply magnetic-button;
  background: rgba(255, 255, 255, 0.06);
  color: rgb(var(--foreground));
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.magnetic-button-secondary:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(0, 188, 235, 0.4);
}

@utility magnetic-button-ghost {
  @apply magnetic-button;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
}
.magnetic-button-ghost:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgb(var(--foreground));
}

@utility magnetic-input {
  @apply w-full px-3 py-2 rounded-magnetic placeholder-surface-300 focus:outline-hidden;
  background: rgba(15, 15, 26, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgb(var(--foreground));
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: border-color 180ms ease-out, box-shadow 180ms ease-out;
}
.magnetic-input:focus {
  border-color: rgba(0, 188, 235, 0.6);
  box-shadow: 0 0 0 3px rgba(0, 188, 235, 0.15), 0 0 18px rgba(0, 188, 235, 0.2);
}
```

**Button hierarchy rule:** one primary per visible region. Everything else is secondary or ghost. The primary's gradient + glow is the loudest thing on the page; if you have two, neither reads as primary.

---

## 8. Layout Pattern (the page shell)

The app uses a **floating-rail layout** — a fixed left-side glass rail that expands on hover, no top header, content scrolls in a centered max-width column.

```tsx
// Layout.tsx — wrap routes in this
export function Layout({ children }) {
  return (
    <div className="relative h-screen w-screen overflow-hidden">
      <AuroraBackground />            {/* fixed z-0 gradient */}
      <Sidebar />                      {/* fixed glass rail, 16px from edges */}

      <main
        className="relative z-10 h-full overflow-auto
                   pl-3 md:pl-[76px]    /* leave a lane for the rail */
                   pr-3 md:pr-6
                   pt-20 md:pt-6 pb-6"
      >
        <div className="mx-auto max-w-[1600px] h-full">
          {children}
        </div>
      </main>
    </div>
  )
}
```

**Sidebar pattern:** fixed left-3 top-3 bottom-3, `glass-rail rounded-glass`, collapses to 64px (icons only) and expands to 240px on `mouseenter` / `focusWithin`. Active route gets:

- Icon in `text-primary` with `drop-shadow-[0_0_6px_rgba(0,188,235,0.6)]`
- A 2px left-edge bar `bg-primary` with cyan glow (`box-shadow: 0 0 8px rgba(0,188,235,0.7)`)
- Background `bg-primary/10`

Section labels in the rail use `eyebrow` utility (uppercase, tracked, 11px, 55% white).

---

## 9. Component Recipes

### Card
```tsx
<div className="magnetic-card">{children}</div>
// equivalent to glass-pane with p-4
```

### Stat / Metric card
```tsx
<div className="magnetic-card">
  <div className="flex items-center gap-3 mb-2">
    <Icon className="w-5 h-5 text-primary" />
    <span className="text-surface-300 text-sm">{label}</span>
  </div>
  <div className="flex items-baseline gap-1">
    <span className="text-2xl font-semibold">{value}</span>
    {unit && <span className="text-surface-400 text-sm">{unit}</span>}
  </div>
</div>
```

### Hero number
```tsx
<div className="display-hero text-gradient-primary">{value}</div>
<div className="eyebrow mt-2">{label}</div>
```

### Status pill
```tsx
<span className="glass-pill px-3 py-1 text-xs flex items-center gap-2">
  <span className="live-dot text-success" />
  Online
</span>
```

### Modal
```tsx
<div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
  <div className="glass-pane-strong p-6 max-w-md w-full animate-fade-in">
    {children}
  </div>
</div>
```

### Severity callout
```tsx
<div className="magnetic-card glow-critical">
  <h3 className="text-error font-medium">Alert</h3>
  ...
</div>
```

---

## 10. Motion Vocabulary

Add these animations and reach for them sparingly. Motion is signal, not decoration.

```css
@keyframes fade-in        { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slide-down     { from { opacity: 0; transform: translateY(-100%); } to { opacity: 1; transform: translateY(0); } }
@keyframes ripple {
  0%   { box-shadow: 0 0 0 0 rgba(0, 188, 235, 0.5); }
  70%  { box-shadow: 0 0 0 18px rgba(0, 188, 235, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 188, 235, 0); }
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 currentColor, 0 0 12px currentColor; opacity: 1; }
  50%      { box-shadow: 0 0 0 6px transparent, 0 0 24px currentColor; opacity: 0.6; }
}
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

.animate-fade-in    { animation: fade-in    0.25s cubic-bezier(0.2, 0.8, 0.2, 1); }
.animate-slide-down { animation: slide-down 0.3s  cubic-bezier(0.2, 0.8, 0.2, 1); }
.animate-ripple     { animation: ripple     1.4s  ease-out infinite; }
.animate-pulse-glow { animation: pulse-glow 2s    ease-in-out infinite; }

.live-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: currentColor; box-shadow: 0 0 8px currentColor;
  animation: pulse-glow 1.6s ease-in-out infinite;
}

.streaming-cursor {
  display: inline-block; width: 0.5em; height: 1em; margin-left: 2px;
  vertical-align: text-bottom;
  background: linear-gradient(180deg, #00bceb, #7c5cff);
  border-radius: 1px;
  box-shadow: 0 0 8px rgba(0, 188, 235, 0.7);
  animation: pulse-glow 1.2s ease-in-out infinite;
}
```

**Use motion for:**
- Mount transitions (fade-in 250ms, slide-down 300ms — never longer)
- Live state (pulse-glow on a streaming/recording dot)
- Confirmed updates (ripple briefly when data refreshes)

**Don't use motion for:**
- Decoration. Bouncing cards or always-on shimmer cheapens the system.
- Long durations (>400ms feels sluggish; aurora drift is the only exception)

---

## 11. Accessibility (do not skip)

```css
@layer base {
  :focus-visible {
    @apply outline-hidden;
    box-shadow: 0 0 0 3px rgba(0, 188, 235, 0.5), 0 0 0 5px rgba(15, 15, 26, 0.9);
  }
}

/* Reduced motion — kill the aurora drift but keep transitions snappy */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .aurora-canvas::before { animation: none !important; }
}

/* High contrast — opaque the glass */
@media (prefers-contrast: high) {
  :root { --color-primary: #00d4ff; --aurora-intensity: 0.25; }
  .magnetic-card, .glass-pane, .glass-pane-strong, .glass-pane-subtle {
    border-width: 2px;
    background: rgba(15, 15, 26, 0.92);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}
```

Plus a user-toggleable "calm mode" — set `class="calm-mode"` on `<html>` to kill drift + ripples while preserving the rest:

```css
:root.calm-mode .aurora-canvas::before,
:root.calm-mode .ripple-on-update,
:root.calm-mode .pulse-glow,
:root.calm-mode .shimmer { animation: none !important; }
```

Touch targets: minimum 44×44px on interactive elements (`@apply min-h-[44px] min-w-[44px]`).

---

## 12. Light Mode (optional but supported)

The system supports a light mode by inverting the surface scale. Apply `class="light"` to `<html>`:

- Surfaces flip (light backgrounds, dark text)
- Aurora intensity drops to `0.18` (still present, but a whisper)
- Glass blur values stay the same — the math still works

The light mode is intentionally less interesting than dark. The system is dark-first; light is the courteous fallback. Don't redesign for light mode — just confirm it's readable.

---

## 13. The Don'ts (these break the look)

- ❌ **Don't add second accent colors.** Only cyan (`#00bceb`). Aurora violets/teals stay in the gradient and gradient text. Severity colors stay in glows.
- ❌ **Don't use solid card backgrounds** (`bg-surface-700` etc.) when you should use `glass-pane`. The aurora bleed-through is the whole point. Solid surfaces look flat.
- ❌ **Don't drop shadows.** The system uses inset highlights + colored glows + occasional `--shadow-elev-*`. Default Tailwind `shadow-md` looks wrong here.
- ❌ **Don't fill alerts with red/yellow.** Use the severity glow utilities (`glow-critical`, `glow-warning`). The card stays glassy; the halo carries the meaning.
- ❌ **Don't animate on hover for everything.** Glass-interactive cards lift; buttons lift 1px on primary. Most things stay still.
- ❌ **Don't put gradient text everywhere.** Reserve `text-gradient-aurora` for hero stats, the brand wordmark, and one or two other landmark moments per page.
- ❌ **Don't skip the noise overlay** on the aurora canvas. Without it, banding is obvious on most monitors.
- ❌ **Don't use `border-radius` values other than 8px (buttons/inputs), 12px (subtle panes), 16px (cards/modals/rails), or 9999px (pills).** A jumbled radius scale dissolves the system.

---

## 14. Quick Replication Checklist

If the agent does these in order, the app should feel like Jarvis by the time step 5 is done:

1. **Install** Tailwind v4 + clsx + lucide-react + Inter/JetBrains Mono fonts.
2. **Paste Section 3 + 4 + 6 + 7 + 10 + 11** into the global CSS file (one file, top of import order).
3. **Mount `<AuroraBackground />`** (Section 5) once at the app root. Verify the gradient drifts and the time-of-day class flips on `<html>`.
4. **Build the page shell** (Section 8): floating left rail with `glass-rail rounded-glass`, content area with `max-w-[1600px]` and the offset for the rail.
5. **Replace existing card markup** with `magnetic-card` / `glass-pane`. Replace primary buttons with `magnetic-button-primary`. Replace inputs with `magnetic-input`.
6. **Audit the page for don'ts in Section 13.** Most "still feels off" issues come from accidental solid surfaces or extra accent colors that crept in.
7. **Verify `prefers-reduced-motion` and `prefers-contrast: high`** both produce a usable page.
8. (Optional) Add the calm-mode toggle and light-mode toggle in your settings UI.

---

## 15. What to Customize per App

Three things you should change to make it feel like *your* app and not a clone:

1. **Brand wordmark.** Replace the "J" mark in the rail with your icon, and use a different gradient on the wordmark text (e.g. swap the `text-gradient-aurora` palette in Section 3 for hues that match your brand).
2. **Aurora hue stops.** The `--aurora-h1/h2/h3` time-of-day values in Section 3 are tuned for cyan/violet/magenta. Shift them to your brand hues — keep three stops, keep the night/dusk versions warmer than dawn/day.
3. **Primary accent.** Cyan `#00bceb` is the Jarvis signature. If you change it, change *only this* — don't add a second accent. Pick a hue that contrasts the aurora background (a primary that gets lost in the gradient kills the focus system).

Don't touch radii, shadow-elev, motion durations, or font weights. Those are load-bearing.

---

That's the whole system. The CSS file is ~700 lines, the layout is ~50 lines, and the component recipes are 5–15 lines each. The aesthetic comes from the tokens and the aurora layer doing the heavy lifting — you're not building 100 components, you're building 5 and letting the surface vocabulary carry the rest.
