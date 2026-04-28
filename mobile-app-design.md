# Propglue Mobile App — v1 Design

> **Note:** This doc lives on `mannys-scripts/claude/mobile-app-design-1ZHsG` as a placeholder. Implementation lives in the propglue repo. Items marked **TBD** depend on inspecting propglue's codebase.

---

## Goals

- Mobile is the **primary capture surface** for equipment data (photos, annotations, voice notes), not a thin companion to the web app.
- Distinct, role-specific surfaces for super, property manager, and owner — each one optimized for what that role actually does on a phone.
- Offline-tolerant for supers in basements, mechanical rooms, and dead zones. "Works without signal" is a hard requirement, not a stretch goal.

## Non-goals (v1)

Explicitly cut from scope: meter readings, work order check-off as a daily ritual, time/labor logging, parts/inventory tracking, lease quick-lookup, showings, service request triage, violation acknowledgement, elevator reservation triage as a primary workflow.

The mobile app is a companion focused on field data capture and on-the-go decisions. Desktop propglue remains the source of truth for everything administrative.

---

## Primary users & workflows

### Super (loading dock, basement, roof)

1. **Equipment scan → photo → annotate → sync.** Scan asset tag (or pick from building list when no tag), capture photo, annotate with arrows/circles/text, attach to equipment record. Offline-first; queues uploads.
2. **Voice notes on equipment.** Hands-dirty alternative to typing.
3. **Maintenance orders.** View MOs assigned to me, update status, attach photos and voice notes. No daily "tap to check off" interaction — status updates are intentional, not incidental.
4. **One-tap call to on-call contractor.** When something breaks, the right plumber/HVAC/electrician for this building is one tap away. Pulled from the contact directory.

### Property manager (driving between buildings, walking units)

1. **Universal contact directory.** Tenants, contractors, vendors, staff, building contacts. One-tap call/text/email. Filter by building, by role, by trade.
2. **Walk-through inspection mode.** Checklist + photos per item. Templates per inspection type (annual, move-in/move-out, due diligence). Offline.
3. **Geofenced "what's at this building" dashboard.** Open MOs, recent violations, ticklers due. Auto-loads when the PM is physically near or at the building.
4. **In-app messaging.** Threaded, scoped to a unit / equipment / MO. Context follows the message — beats SMS.
5. **Super visibility.** "Last seen at" status for supers assigned to my buildings (see below).

### Owner (rarely opens, but when they do it must be one screen)

1. **Portfolio glance.** Occupancy %, arrears total, critical open issues, this month's NOI delta.
2. **Approval inbox.** Push notification → tap → approve / deny. Large expenditures, lease applications, anything currently emailed for sign-off. This is the killer mobile feature for owners.
3. **Read-only document access.** Current rent roll, monthly P&L, recent inspection reports. View, not edit.

### Cross-cutting features

- **QR / asset-tag scan** as a universal entry point. Scan → opens the right record (equipment, unit, building).
- **Document camera with OCR.** Invoices, receipts, signed forms. Hybrid on-device + server pipeline.
- **Geofence-aware home screen.** Auto-scopes to the building you're at; eliminates wrong-building data-entry mistakes.

---

## Architecture

### Shell strategy: PWA first, Capacitor wrap second

Ship a Progressive Web App at `app.propglue.com` for v1. Wrap in Capacitor (not React Native) for App Store presence in v2 if iOS Web Push reliability proves insufficient.

**Why PWA first**
- Existing Next.js 15 frontend → ~a week of work for `next-pwa`, manifest, service worker, iOS splash screens.
- Existing httpOnly session cookies work unchanged from a PWA.
- One codebase, instant deploys, no review cycles.

**Why Capacitor (not React Native) when we wrap**
- Capacitor wraps the existing PWA — no parallel codebase. RN means rebuilding every screen.
- Gives us APNs/FCM, native camera, App Store presence without forking the stack.
- None of our v1 workflows need 60fps native interactions.

**Tradeoff to plan around**
- iOS Web Push requires "Add to Home Screen" first. Field PMs may not do that step. If usage data shows poor install rate, accelerate the Capacitor wrap.

### Offline strategy

The non-negotiable architectural constraint, since the super on the loading dock is the primary user.

- **Service worker** for app-shell caching and request interception.
- **IndexedDB** for local data: equipment records for assigned buildings, MO assignments, contact directory, inspection templates, queued mutations.
- **Mutation queue** with retry. Every offline write — photo upload, annotation, voice note, MO status change, inspection result — gets a UUID, lands in the queue, syncs when online.
- **Conflict resolution:**
  - Photos and voice notes: append-only, no conflicts possible.
  - Equipment field edits: last-write-wins with a "your change overwrote a server change made at HH:MM by ___" toast on detection. Don't silently swallow.
  - MO status: server-authoritative. Local change is provisional until acknowledged.
- **Sync indicator.** Persistent UI element shows "X items pending sync" with a tap-to-see-list. Never silent.
- **Cache scope:** equipment + MOs + contacts for buildings the user is assigned to. Not the whole portfolio. Recompute on assignment change.

### Push notifications

Add push as the third channel alongside the existing email + SMS notification service.

- **PWA path:** Web Push via VAPID. Same backend, new channel adapter.
- **Capacitor path (later):** APNs and FCM via Capacitor's push plugin. The notification service abstracts the channel; adding APNs/FCM is a provider config, not a rewrite.
- **Routing:** per-role topic subscriptions (super-mo-assigned, pm-violation-new, owner-approval-pending, etc.). Users opt in/out per topic.
- **Anti-spam discipline:** push is for things requiring action or time-sensitive awareness. Everything else stays in email.

### Super location tracking — "last seen at" model

Designed deliberately gentle to avoid an HR / labor problem.

- **On-duty toggle, not 24/7.** Super taps "I'm working" to start; tracking ends at clock-out or after N hours of inactivity. Even though we're not doing time logging, the toggle is required for tracking to be on.
- **Building-level granularity, not GPS pin.** Recorded as `(super_id, building_id, timestamp)` whenever the device geofences into a building (or scans a tag at one). PM sees: "Marco — last seen at 425 W 23rd, 14 min ago." No live dot on a map.
- **Visibility scoped to assigned PMs.** Only PMs of buildings that super covers can see their last-seen status. Not org-wide.
- **Super sees what's recorded about them.** Personal audit log: "your last-seen status was viewed by Sarah Chen at 2:14pm." Transparency cuts the surveillance feel.
- **Disclosure + consent at onboarding.** First time a super installs the app, an explicit screen explains what's tracked, by whom, and when. Required acceptance. In NYC / California / other jurisdictions this is a legal requirement, not a nicety.
- **Surfacing.** Appears on the PM's "what's at this building" dashboard as a small chip. Optionally on a building-cluster map view (zoom-out) showing which buildings have a super present right now.

What we are **not** building in v1: live GPS dots, route history, time-on-site reports, geofence violation alerts. Those slide a clean tool into surveillance territory; revisit only with explicit demand and a labor-policy review.

### QR / asset-tag scan

- **Dependency:** main propglue app needs to generate and manage asset tag IDs and produce a printable label format. **TBD** — does this exist today?
- **Format:** short opaque ID encoded as QR. Optionally a fallback URL that opens the mobile app or web record.
- **Scan flow:** camera scan → resolve ID → open the right record. Works offline if the record is in the local cache.
- **Print workflow:** lives in the main web app, not the mobile app. Mobile only consumes tags.

### Document camera + OCR

"Seamless" splits into a hybrid pipeline:

- **On-device fast path.** Apple Vision (iOS), ML Kit (Android), browser-native APIs (PWA). Instant edge detection, perspective correction, multi-page capture, immediate feedback.
- **Server-side reconciliation.** For invoices and receipts where structured fields matter (vendor, amount, date, invoice #), send to Textract / Google Document AI / similar. Returns parsed fields, attaches them to the record.
- **Auto-attach in context.** If you open document camera while viewing a vendor record, the resulting scan defaults to that vendor and skips the picker. Most scans should land in the right place with zero taps.
- **Document types in v1:** invoices, receipts, signed forms (acknowledgement only — not e-signature). Other types skip OCR and store as plain images.
- **Quality discipline:** if OCR confidence is below a threshold, surface the parsed fields for user confirmation rather than silently filing wrong data.

### Auth

- Reuse existing httpOnly session cookies. PWA fetch and Next.js routes work unchanged.
- iOS PWA: cookies persist after "Add to Home Screen." Verify behavior on iOS 17+.
- When wrapped in Capacitor: WebView shares cookies, or refactor to a bearer token model if WebView session sharing is fragile across iOS versions. Decide at wrap time.

---

## Data model touchpoints — **TBD pending propglue access**

Entities the mobile app reads or writes. Schema details deferred until I can see the codebase.

- **Equipment** — id, building, type, model, serial, photos[], annotations[], voice notes[], asset tag id
- **Maintenance order** — assignee, building, equipment ref, status, photos[], voice notes[], created/updated
- **Contact** — person with phone/email/role, scoped to building(s) or org-wide
- **Building** — geofence coords (or geocodable address), super assignments, on-call contractor mapping by trade
- **Document** — image(s), OCR result, attached-to record
- **Approval request** — owner-bound, type (expense / lease / other), payload, status
- **Super last-seen** — super_id, building_id, timestamp, source (geofence | tag scan | manual)
- **Push subscription** — user_id, endpoint, p256dh, auth, topic subscriptions, device

---

## Phased rollout

- **Phase 0 — Foundation.** PWA shell, manifest, service worker, auth via existing session cookies, navigation skeleton, Cameras tab parity (matches what web does today).
- **Phase 1 — Super primary loop.** Equipment scan → photo capture → annotation → offline queue → sync. The core. Validates offline architecture end-to-end.
- **Phase 2 — Super extensions.** Maintenance orders (view + update), voice notes, one-tap contractor call.
- **Phase 3 — PM core.** Universal contact directory, walk-through inspection mode with templates, geofenced building dashboard.
- **Phase 4 — Super location.** "Last seen at" with on-duty toggle, consent flow, PM visibility, super audit log.
- **Phase 5 — Owner.** Portfolio glance, approval inbox (with push), read-only documents.
- **Phase 6 — Document camera + OCR.** Basic capture lands in phase 1 (it's just a camera). OCR pipeline and structured extraction land here.
- **Phase 7 — Capacitor wrap.** Triggered by iOS Web Push reliability data, not a fixed date. Skip if PWA is sufficient.

---

## Open questions

1. Does propglue's main app generate asset tag IDs and printable labels today? If not, that's a parallel workstream blocking phase 1.
2. What's the equipment registry schema? How are equipment records related to buildings and MOs?
3. Are buildings geofenced? Do we have lat/lng on building records, or addresses we need to geocode?
4. Is there an existing "on-call contractor by trade by building" mapping, or do we build it?
5. What's the current notification service architecture? Adding Web Push as a channel — drop-in, or does it need a provider abstraction first?
6. iOS "Add to Home Screen" rate — how do we drive that step? Critical for Web Push to work at all on iOS.
7. Inspection templates — who authors them? Is template authoring part of the main app or mobile?
8. What's the owner approval surface on web today? Mobile needs functional parity.
9. Tag format choice — opaque ID vs URL — affects fallback behavior when scanned by a non-app camera.
10. Voice note storage — duration cap, transcription (yes/no), retention.

## Risks

- **iOS Web Push reliability** — the single biggest variable. Drives the Capacitor wrap decision and may force it earlier than planned.
- **Super location tracking → labor / legal exposure** if rolled out without the consent and disclosure flow. Don't let this ship without sign-off from whoever handles labor policy at propglue.
- **OCR quality variance** — receipts and invoices are easier than handwritten forms. Set expectations on which document types are supported; refuse silent failures.
- **Offline conflicts on equipment edits** — last-write-wins is the default but needs UI to surface overwrites. Don't pretend conflicts can't happen.
- **Cache scope explosion** — a PM with 200 buildings shouldn't sync 200 buildings of equipment to their phone. Smart eviction and on-demand fetch.
- **Asset tag generation dependency** — if the main app doesn't have it, phase 1 stalls. Validate this first.
