# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary (evaluated context):** interviewers and engineering reviewers watching a live demo. They probe the app the way they would probe a candidate: click the fake-looking controls, open DevTools, try illegal transitions. Success = the app survives scrutiny and demonstrates engineering judgment.
- **Admin (demo operator):** the person presenting. Manages orders (status machine), users (roles), products, and sends notifications (targeted + broadcast). Uses the workspace daily during prep.
- **Member (normal user):** a storefront customer account. Browses the catalog, places orders, follows restock alerts, edits own profile/password. Inferred assumption (labeled): members exist mostly so role-based UI can be demonstrated; their flows should feel like a real small shop, not an internal tool.

## Product Purpose

Backend Lab is a fullstack engineering showcase: session-cookie auth with revocation, RBAC, an order state machine, RQ-driven notifications (targeted + broadcast + restock edge-trigger), and a product catalog — fronted by a Vue 3 storefront/member center and an admin workspace. Success means the demo tells a coherent engineering story end to end without the UI contradicting the backend's honesty.

## Positioning

The mechanism a neighboring demo cannot copy: **the UI is wired to the architecture it demos** — legal state transitions disabled in-place, session revocation observable (change password → signed out everywhere), live readiness probes in the chrome, notification fan-out visible in the bell. The design must never fake data the backend can actually provide.

## Operating Context

Used live in interviews (screen share, often one interviewer following along), and locally via Docker Compose (api + postgres + redis + workers + Vite dev). Sessions revolve around: browsing catalog → order + pay → admin advancing status → notifications arriving. English UI; owner communicates in Traditional Chinese.

## Capabilities and Constraints

- Roles: visitor (public catalog), member (auth), admin (workspace + admin pages). Role-based chrome is a hard requirement.
- Order state machine is the source of truth (`app/core/enums.py`): created → pending → processing → completed (+cancelled). Illegal transitions must be un-selectable.
- Session cookies are HttpOnly; the UI never touches tokens.
- Notifications: personal (General) vs broadcast (System) are distinct feeds; unread badge counts General only.
- Light mode is pinned to the owner's swatch: #776B5D / #B0A695 / #EBE3D5 / #F3EEEA. No purple anywhere. Dark mode is required (colors delegated to design).
- Sans-serif type. Demo must work offline-ish: no hard dependency on network fonts for layout correctness.
- Undecided: registration page UI, order detail editing, bulk admin actions (roadmap P2+).

## Brand Commitments

- Name "Backend Lab" with the bolt mark (kept; treatment may change).
- Warm cream palette as pinned above; warm taupe ink; no purple/violet anywhere (owner rejected it explicitly).
- Honest-chrome principle (owner-endorsed through feedback): real stats over decorative numbers; fake controls removed rather than decorated.

## Evidence on Hand

- PRD v1.5 (`docs/PRD.md`) — authoritative feature/contract spec.
- DESIGN.md + `.impeccable/design.json` — the cream "Warm Paper & Ink" token world from the current implementation (owner rejected the UI composition built on it, palette stays).
- Live demo data: real users/orders/products/notifications in Postgres.

## Product Principles

1. **Honest chrome** — nothing in the UI claims what the backend doesn't; every control works or disappears.
2. **The state machine is the design** — transitions, badges, and locks visualize the domain truthfully.
3. **Two voices, one paper** — airy member/shop surfaces, dense admin surfaces, same material world.
4. **Demo-grade scrutiny** — every screen must survive an interviewer clicking everything.

## Accessibility & Inclusion

- WCAG AA contrast on all text (enforced in tokens; verified by hand-computation during the cream implementation).
- Full keyboard operability for primary flows; Esc closes floating panels; visible focus everywhere.
- `prefers-reduced-motion` honored globally.
