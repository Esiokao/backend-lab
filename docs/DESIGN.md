---
name: Backend Lab
description: Warm cream (light) / warm charcoal (dark) member-and-admin console for a fullstack interview demo — "Engineering Vellum" two-mode world.
colors:
  paper: "#f3eeea"
  paper-deep: "#ede5d9"
  cream: "#ebe3d5"
  card: "#fbf8f3"
  card-soft: "#f6f1e9"
  ink: "#3e372c"
  ink-strong: "#2e2921"
  ink-soft: "#6b6152"
  ink-faint: "#756a58"
  line: "#dfd4c4"
  line-soft: "#e7decf"
  line-strong: "#c9bca8"
  brand: "#776b5d"
  brand-strong: "#655b4e"
  brand-deep: "#554c40"
  on-brand: "#fdfbf7"
  success: "#5f7d5c"
  success-bg: "#e7ede2"
  success-ink: "#44603e"
  danger: "#a9553f"
  danger-bg: "#f5e4dd"
  danger-ink: "#8f4432"
  warning: "#9a7729"
  warning-ink: "#7e5f1f"
  warning-bg: "#f4ead2"
  info: "#5e6e7d"
  info-bg: "#e8ebee"
  honey: "#b98a2e"
typography:
  display:
    fontFamily: "DM Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "DM Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "DM Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "DM Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "10px"
    fontWeight: 700
    letterSpacing: "0.08em"
  data:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "12.5px"
    fontWeight: 600
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "14px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "13px"
  lg: "21px"
  xl: "44px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.on-brand}"
    rounded: "{rounded.md}"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.brand-strong}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    height: "34px"
  panel:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.lg}"
  status-badge:
    backgroundColor: "{colors.card-soft}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.pill}"
---

# Design System: Backend Lab

## Overview

**Creative North Star: "Warm Paper & Ink" — the Engineering Vellum direction**

The interface is a drawing sheet: every page opens with a **title block** (sheet code, revision, live figure) the way an engineering sheet does, the ground carries a faint drafting grid, key figures get **dimension-line callouts**, and tables read as schedules of components. Chosen direction (IMPECCABLE'S PICK) from a concept-seed hand; palette pinned by the owner.

Two modes on one material world: **light** = cream bond paper (pinned swatch #776B5D / #B0A695 / #EBE3D5 / #F3EEEA); **dark** = the same sheet under lamplight — matte warm charcoal (#211d17), cream ink, taupe hairlines (donor discipline: the Catalog Sleeve challenger). Theme is user-togglable (avatar menu), persisted in localStorage, applied pre-paint via an inline script in index.html.

Interactive emphasis stays monochrome taupe; the few status hues (sage, terracotta, honey, slate) carry real meaning. Statuses render as rectangular **stamps** (1.5px currentColor border, transparent fill) — a nod to the Letterpress and Ticket-Wallet challengers ("nothing disappears, it cancels").

**Key Characteristics:**
- Warm cream grounds, never pure white and never gray — every neutral is tinted from the taupe hue.
- Ink hierarchy espresso > taupe; no gray text anywhere.
- Data (prices, ids, dates) set in JetBrains Mono with tabular numerals.
- One restrained entrance animation per surface section (rise-in), pop-in for floating panels; all disabled under `prefers-reduced-motion`.

## Colors

A four-swatch pinned palette (#776B5D / #B0A695 / #EBE3D5 / #F3EEEA) expanded into a tinted token system. All text hues pass WCAG AA (≥4.5:1) on their grounds; nothing is gray.

### Primary
- **Dark Taupe** (#776b5d): primary buttons, brand mark, active icons. White-range text on it measures 5.1:1.
- **Brand Deep** (#554c40): links, order/user ids, pressed accents.

### Neutrals
- **Light Cream Paper** (#f3eeea): page ground.
- **Cream Panel** (#ebe3d5): wells, unread rows, active-tab fill.
- **Warm Card** (#fbf8f3): card and panel surfaces.
- **Espresso Ink** (#3e372c): body text. **Strong Ink** (#2e2921): headings and numeric emphasis.
- **Taupe Soft** (#6b6152) / **Taupe Faint** (#756a58): secondary and meta text; both ≥4.5:1 on card and paper.
- **Parchment Lines** (#dfd4c4 / #e7decf / #c9bca8): the only border colors.

### Status
- **Sage Success** (#5f7d5c / ink #44603e on #e7ede2): completed, in-stock, live probes.
- **Terracotta Danger** (#a9553f / ink #8f4432 on #f5e4dd): destructive, cancelled, unread badges.
- **Honey Warning** (#9a7729 dot / ink #7e5f1f on #f4ead2): pending, out-of-stock.
- **Slate Info** (#5e6e7d on #e8ebee): processing.
- **Honey Star** (#b98a2e): followed-product star only.

## Typography

DM Sans (humanist sans) carries everything; JetBrains Mono is reserved for data (prices, ids, timestamps-as-data). Ramp: display 28px/700 → panel headline 15px/600 → body 13px → meta 11–12px → label 10px uppercase tracked. No 9px text anywhere; table cells 12.5px.

## Layout

The title block (`.page-heading`): 1.5px brand border, `th-main` (h1 + lede) plus `th-cell`s (SHEET code, REV/date, live figures) separated by hairlines; stacks vertically ≤760px. The drafting grid (`--grid-line`, 28px two-axis repeating gradient) sits only on content grounds — the world that earns it.

Sidebar 244px fixed (hidden ≤760px, replaced by horizontal chip nav). Content column `min(1180px, 100% − 80px)`. Metric grids 4→2→1 columns at 1050px/480px. Tables keep a 680px min-width and scroll horizontally inside panels. Panels and fields ride a 12/13px spacing rhythm; more space above a heading than below.

## Elevation & Depth

Two shadow tokens only: ambient card (`0 1px 2px + 0 10px 28px` warm brown at 5–7%) and pop (floating panels, `0 18px 44px` at 16%). Cards pair a 1px parchment border with the ambient shadow; floating panels (notifications, avatar menu) use pop + `pop-in` scale entrance. No glows, no zero-offset halos.

## Shapes

Radius ramp 6/8/12/14px; 999px reserved for badges, pills, and avatars. Cards 12px, floating panels and login card 11–14px, buttons and inputs 6–8px. Border language: 1px parchment lines everywhere; borders darken (`--line-strong`) on hover rather than growing.

## Components

- **Primary button**: taupe fill, cream text, subtle lift on hover; disabled at 50% opacity.
- **Ghost button**: transparent with parchment border; hover gains card fill.
- **Panel**: warm card with header (title + meta) and 1px dividers; tables scroll inside.
- **Status/role badges**: pill, tinted background + darker same-hue ink; uppercase 10px/600.
- **Notifications panel**: 340px floating card with General/System tabs (badge counts), unread rows tinted cream.
- **Avatar menu**: 236px floating card, greeting header, icon+label items, danger-toned sign-out.

## Do's and Don'ts

- **Don't** introduce gray text or pure white/black anywhere; tint neutrals from the taupe hue.
- **Don't** use purple, neon, glow shadows, or gradient text — the world is matte paper.
- **Don't** add kicker/eyebrow labels above headings; the heading speaks alone.
- **Don't** ship text below 11px; meta lives at 11–12px and must keep 4.5:1.
- **Don't** hardcode ground/glass colors — every surface rides tokens so both themes inherit.
- **Do** add the dark counterpart (`[data-theme="dark"]` block) whenever a new color token is introduced.
- **Don't** fake data in chrome (status pills, environment labels) — wire it to the real endpoints or remove it.
- **Do** set any numeric data in JetBrains Mono with tabular numerals.
- **Do** keep entrance motion one `rise-in` per section with ≤0.2s stagger, and honor `prefers-reduced-motion`.
