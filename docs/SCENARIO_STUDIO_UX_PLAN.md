# Scenario Studio UX Improvement Plan

## Context

The Scenario Studio is a React Flow canvas editor where users build OT network scenarios by dragging devices from a palette and connecting them with protocol flows. The UI feels **cluttered** and **device cards overlap**. After a thorough code review and design best-practice research, the root causes are:

1. **Default node spacing is too tight** — `useCanvasSync.ts:38-41` places devices at 180px horizontal / 150px vertical, but cards are 140-180px wide with 12px+16px padding, leaving only ~0-40px gap
2. **No collision detection** — dropping or moving nodes has zero overlap prevention
3. **High information density** — each device card shows icon (56x56), name, vendor, role, IP, up to 4 protocol badges, config status, and CVE badge — all in a 140-180px wide card
4. **Panel overhead** — left palette (280px) + right panel (360px) = 640px reserved, leaving only ~800px for the canvas on a 1440px screen
5. **No responsive design** — zero media queries, fixed widths everywhere
6. **No semantic zoom** — same card detail at every zoom level

---

## Easy Wins (1-3 hours each) — COMPLETE

### E1. Fix default node spacing — DONE
**File**: `frontend/src/components/canvas/hooks/useCanvasSync.ts:38-41`
- Changed default grid from `180px x 150px` to `250px x 220px`
- Reduced column count from 5 to 4 for more breathing room

### E2. Add fitView on scenario load — DONE
**File**: `frontend/src/components/canvas/ScenarioCanvas.tsx`
- Changed `fitView={false}` to `fitView` with `fitViewOptions={{ padding: 0.15 }}`

### E3. Improve toolbar button grouping with visual separators — DONE
**File**: `frontend/src/components/canvas/CanvasControls.tsx`
- Added labeled groups (View, Edit, Map, Layout, Names, Version) with 9px uppercase muted labels
- Merged Delete into Edit group, shortened button text to icon-only for Save/History

### E4. Collapse device palette groups by default — DONE
**File**: `frontend/src/components/palette/DevicePalette.tsx`
- Changed `defaultActiveKey={Object.keys(groupedDevices)}` to `defaultActiveKey={[]}`

### E5. Tighten device card content — DONE
**File**: `frontend/src/components/canvas/nodes/DeviceNode.tsx`
- Reduced icon container from 56x56px to 40x40px (icon font 28px to 20px)
- Reduced padding from `12px 16px` to `10px 12px`
- Reduced card width from 140-180px to 130-160px
- Vendor text now shown only on hover or selection

### E6. Snap grid alignment improvement — DONE
**File**: `frontend/src/components/canvas/ScenarioCanvas.tsx`
- Changed snap grid from `[16, 16]` to `[20, 20]` to match background grid gap

---

## Medium Effort (0.5-2 days each)

### M1. Compact node mode (zoom-aware card density)
**Files**: `DeviceNode.tsx`, `ScenarioCanvas.tsx`
- Introduce two node render modes based on zoom level:
  - **Normal** (zoom >= 0.6): current card with icon, name, IP, protocols
  - **Compact** (zoom < 0.6): just colored icon circle (32px) + name text below (10px)
- React Flow provides `useStore(s => s.transform[2])` to read current zoom
- This is the simplest form of semantic zoom — massively reduces clutter when zoomed out

### M2. Node overlap prevention on drop
**Files**: `useNodeDrag.ts`, new utility
- When a device is dropped, check if position overlaps any existing node
- If overlap detected, nudge the new node to nearest non-overlapping position
- Algorithm: expand in a spiral pattern from drop point until clear space found
- Use node bounding boxes (width=180, height=200 estimated) + 20px margin

### M3. Resizable sidebars with drag handles
**Files**: `ScenarioStudioPage.tsx`, `uiStore.ts`
- Add CSS `resize` drag handles between left panel / canvas and canvas / right panel
- uiStore already has `setLeftSidebarWidth` / `setRightSidebarWidth` — wire them up
- Set min/max: left 200-400px, right 280-500px
- Persist widths in localStorage (already set up via `persist` middleware)

### M4. Floating toolbar (detach from panel)
**File**: `CanvasControls.tsx`, `ScenarioCanvas.tsx`
- Move toolbar from fixed top-left to a floating bar centered at top of canvas
- Use React Flow's `<Panel position="top-center">`
- Smaller buttons (28px), icon-only with tooltips
- Group with pill-style segmented backgrounds
- Inspired by Figma/Miro floating toolbars

### M5. Device card hover expansion
**File**: `DeviceNode.tsx`
- Default: show only icon + name (compact card)
- On hover (300ms delay): expand card to show IP, vendor, protocols
- On selection: always show full detail
- Uses CSS transitions on max-height
- Dramatically reduces visual clutter without hiding information

### M6. Auto-layout on paste/import
**Files**: `useAutoLayout.ts`, `ScenarioCanvas.tsx`
- When pasting devices or importing a scenario, auto-run Grid layout
- Add "Auto-arrange" button in toolbar (wraps existing grid layout)
- Make it more discoverable — many users don't know about the Layout dropdown

### M7. Improved edge routing
**File**: `FlowEdge.tsx`
- Currently using default Bezier curves which can cross through nodes
- Switch to `smoothstep` edge type for better readability in dense graphs
- Add edge labels that stay readable (currently can overlap with nodes)

---

## Hard Effort (3-7 days each)

### H1. Full semantic zoom system
**Files**: `DeviceNode.tsx`, new `useSemanticZoom.ts` hook
- Three LOD tiers based on zoom level:
  - **Far** (< 0.35): colored dot + 1-letter type label
  - **Medium** (0.35-0.7): icon circle + name, no details
  - **Close** (> 0.7): full card with all details
- Smooth transitions between tiers
- Zone nodes similarly adapt: far = colored rectangle, close = full label + network info

### H2. Smart auto-layout engine with ELK.js
**Files**: `useAutoLayout.ts`, new dependency
- Replace manual layout algorithms with ELK.js (Eclipse Layout Kernel)
- Supports: layered (Sugiyama), force-directed, stress, tree
- Configurable per-scenario: Purdue model maps to layered layout with fixed layer constraints
- Respects zone groupings as compound nodes
- Runs incrementally — can layout just newly-added nodes without disrupting existing positions

### H3. Responsive canvas layout
**Files**: `ScenarioStudioPage.tsx`, `AppLayout.tsx`, `uiStore.ts`
- Add breakpoints:
  - **< 1024px**: left panel auto-collapsed, right panel as overlay drawer
  - **1024-1440px**: left panel collapsible, right panel 300px
  - **> 1440px**: full layout as today
- Panels become slide-over drawers on smaller screens (Ant Design Drawer)
- Canvas always gets maximum available space
- Toolbar wraps to 2 rows or collapses to hamburger menu on narrow screens

### H4. Panel-free "focus mode"
**Files**: `ScenarioStudioPage.tsx`, `CanvasControls.tsx`
- Toggle via keyboard shortcut (F11 or Ctrl+\)
- Hides both sidebars and bottom panel — canvas takes full screen
- Floating mini-controls appear: zoom, layout, undo/redo
- Right-click on device opens floating property popover instead of panel
- Great for presentation and review workflows

### H5. Minimap with navigation
**File**: `ScenarioCanvas.tsx`, minimap config
- Enhanced minimap in corner:
  - Shows zoom rectangle (viewport indicator)
  - Click-to-navigate (jump to area)
  - Device count overlay
  - Zone outlines with labels
- Position in bottom-right with collapse toggle
- Useful for large scenarios (50+ devices)

---

## Moonshot Ideas (1-4 weeks each)

### S1. Spatial clustering / group-by views
- Automatically cluster devices by: zone, protocol, vendor, Purdue level
- Toggle between views: "Show by Zone" / "Show by Protocol" / "Show by Vendor"
- Each view re-layouts the canvas with different grouping logic
- Collapsed clusters show aggregate info (device count, protocol mix)
- Click to expand a cluster into individual devices
- Inspired by network monitoring tools (SolarWinds, Cisco DNA Center)

### S2. Canvas themes / visual presets
- Multiple visual styles for the canvas:
  - **Blueprint** (current dark theme, refined)
  - **Clean white** (light theme for documentation/export)
  - **Cisco topology** (matches Cisco DNA Center styling)
  - **Purdue reference** (background shows Purdue model layers)
- Each theme adjusts: background, node colors, edge styles, font
- Export-aware: white theme produces cleaner PDF/PNG exports

### S3. Animated traffic flow visualization
- When a deployment is running, edges animate with flowing dots/particles
- Dot speed proportional to poll rate, dot color = protocol color
- Pulse animation on nodes receiving traffic
- Visual representation of the traffic the system is generating
- Can be toggled on/off, only during live deployments

### S4. Command palette (Cmd+K)
- Quick-access command palette (like VS Code, Figma, Linear)
- Search devices by name/type/IP, jump to device on canvas
- Run actions: "Apply Purdue layout", "Fit view", "Toggle minimap"
- Search help articles, keyboard shortcuts
- Dramatically improves discoverability of features hidden in menus

### S5. Multi-tab canvas workspaces
- Open multiple scenarios in tabs (like browser tabs or VS Code)
- Quick-switch between scenarios without navigating away
- Copy/paste devices between scenarios (cross-tab DnD)
- Split-view: two scenarios side by side for comparison

---

## Key Files for Implementation

| File | Purpose |
|------|---------|
| `frontend/src/components/canvas/nodes/DeviceNode.tsx` | Device card rendering & sizing |
| `frontend/src/components/canvas/hooks/useCanvasSync.ts` | Default node positioning |
| `frontend/src/components/canvas/hooks/useAutoLayout.ts` | Layout algorithms |
| `frontend/src/components/canvas/hooks/useNodeDrag.ts` | Drop handling |
| `frontend/src/components/canvas/ScenarioCanvas.tsx` | Canvas config & React Flow setup |
| `frontend/src/components/canvas/CanvasControls.tsx` | Toolbar controls |
| `frontend/src/components/panels/RightSidePanel.tsx` | Right panel tabs |
| `frontend/src/components/palette/DevicePalette.tsx` | Device palette |
| `frontend/src/pages/ScenarioStudioPage.tsx` | Studio layout structure |
| `frontend/src/stores/uiStore.ts` | UI state (panel widths, toggles) |
| `frontend/src/index.css` | Global styles & CSS variables |
| `frontend/src/main.tsx` | Ant Design theme config |

## Verification

After implementing any changes:
1. Open an existing scenario with 10+ devices — verify no overlaps
2. Create a new scenario from template — verify fitView works
3. Drag 5+ devices from palette — verify spacing
4. Zoom in/out — verify readability at all zoom levels
5. Toggle sidebars — verify canvas reclaims space
6. Test at 1280px and 1920px browser widths
