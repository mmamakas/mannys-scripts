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

## Offline equipment cache — concrete shape

The super's primary loop (scan → photo → annotate → sync) has to work with zero signal. This is the IndexedDB layout and sync protocol that makes that true. Store names are suggestions; adapt to whatever propglue's equipment schema actually calls things.

### IndexedDB stores

One database, `propglue-mobile`, versioned. Six object stores.

| Store | Key | Indexes | Purpose |
|---|---|---|---|
| `buildings` | `id` | `updatedAt` | Buildings the user is assigned to. Includes lat/lng and geofence radius once the main app has them. |
| `equipment` | `id` | `buildingId`, `assetTagId`, `updatedAt` | Full equipment records for assigned buildings. This is what a tag scan resolves against offline. |
| `contacts` | `id` | `buildingId`, `role`, `trade` | Directory. `trade` index powers one-tap on-call contractor. |
| `maintenanceOrders` | `id` | `buildingId`, `assigneeId`, `status`, `updatedAt` | MOs assigned to this user, plus open MOs for assigned buildings. |
| `mutations` | `id` (UUID) | `createdAt`, `status`, `entityType` | The write queue. Every offline write lands here first. |
| `blobs` | `id` (UUID) | `mutationId` | Photo and voice-note binaries, referenced by mutations. Kept separate so the `mutations` store stays small and fast to scan. |

`meta` is a seventh single-row store holding `lastSyncAt`, `schemaVersion`, and `userId`. If `userId` changes at login, wipe everything.

### Mutation record

```json
{
  "id": "uuid",
  "createdAt": 1758000000000,
  "status": "pending | inflight | failed | done",
  "attempts": 0,
  "lastError": null,
  "entityType": "equipmentPhoto | equipmentAnnotation | voiceNote | moStatus | inspectionItem",
  "entityId": "server id, or a client-generated temp id for creates",
  "payload": { },
  "blobIds": ["uuid"]
}
```

`status` moves pending → inflight → done, or → failed after a bounded number of attempts. Failed mutations are never silently dropped. They show in the pending-sync list with the error and a retry button.

### Sync protocol

**Pull** (on app open, on reconnect, on pull-to-refresh, and on a timer while foregrounded):

1. `GET /api/mobile/sync?since=<lastSyncAt>` returns changed rows across all cached entity types for the user's assigned buildings, plus a list of deleted ids.
2. Upsert into the matching stores. Apply deletes.
3. Write the new `lastSyncAt` only after every upsert commits. A crash mid-pull replays from the old cursor, which is safe because upserts are idempotent.

**Push** (whenever `navigator.onLine` flips true, and after every pull):

1. Read `mutations` where `status = pending`, ordered by `createdAt`.
2. For each, mark `inflight`, send it, and on success mark `done` and delete its blobs. On failure increment `attempts`, store the error, and mark `pending` again or `failed` once the cap is hit.
3. Process strictly in order. A photo upload must land before the annotation that references it.
4. Server responses that include a canonical id for a client-created entity rewrite the temp id in every later pending mutation before those are sent.

Photos upload as multipart to the existing Cameras upload endpoint, since that path already works without QR. Voice notes go the same way with a different content type.

**Background Sync.** Register a one-shot `sync` event with the service worker when a mutation is enqueued. Chrome and Android honor it. Safari does not, so iOS relies on foreground push. Do not design around Background Sync being reliable.

### Conflict rules

Stated in the offline strategy above, restated here in terms of the stores:

- `equipmentPhoto`, `voiceNote`, `inspectionItem`: append-only. Never conflict.
- `equipmentAnnotation`: last-write-wins per annotation id. Annotations are small independent objects, not one big blob, so two supers annotating the same photo do not clobber each other.
- `moStatus`: server-authoritative. The local row shows the optimistic status with a "pending" badge until the server confirms. If the server rejects it (someone else closed the MO first), revert the local row and surface a toast.

### Cache scope and eviction

- Cache **only** buildings the user is assigned to. A PM with a large portfolio gets the buildings in their assignment list, nothing else. Recompute the list on every pull and evict rows for buildings that dropped out.
- Equipment, contacts, and MOs for those buildings are cached in full. They are small text rows. Even a large building is tens of kilobytes.
- Photos already on the server are **not** cached locally. Thumbnails are fetched on demand and cached by the service worker with a size cap. Full-res is network-only.
- Blobs in the `blobs` store are deleted the moment their mutation reaches `done`. The store should be near-empty on a healthy device.
- If storage quota is hit, refuse new captures with a clear message rather than evicting pending uploads. Losing a super's photos is worse than blocking a new one.

---

## Findings from the public PropGlue repos

Read on 2026-09-15 from `mmamakas/propglue-docs` and `mmamakas/propglue-mobile-design`. The main `mmamakas/propglue` repo is private and was not readable from this session, so schema and service details remain **TBD**.

### Platform facts that affect this design

- **Super is a view-only role today.** The team-invite flow lists Super as "view-only for specific buildings." The super's core mobile loop (photo, annotate, voice note, MO status) requires write access. Either the Super role gains scoped write permissions on equipment and MOs, or a new field-tech role is introduced. This is a main-app change and a phase-0 prerequisite.
- **Photos already support annotation on web** ("capture conditions, annotate images, and link to projects"). The mobile annotation feature should reuse that data model rather than invent one.
- **Existing modules:** Buildings, Documents, Permits & Violations, Contractors, Equipment, Capital Projects, Secure Vault, Photos, NYC DOB integration, audit logs, RBAC. Equipment tracking is confirmed as an existing module, which is good for phase 1.
- **No Maintenance Orders module is listed.** Capital Projects exists, but nothing named work orders, tickets, or maintenance orders. Either MOs live somewhere the docs do not mention, or they need to be built in the main app before the mobile MO feature can exist.
- **No Tenants module is listed.** Contractors are a first-class module, but tenant contacts are not visible in the docs. The universal directory depends on tenant records existing in the main app.
- **Buildings carry NYC identifiers** (BIN, block and lot, borough). No lat/lng is mentioned. Geofencing needs geocoding from the address, which is a small main-app addition.

### Conflicts with the April 2026 mobile design

`propglue-mobile-design/docs/requirements/building-ops-mobile.md` (v1.0, dated 2026-04-22) describes a different product than the one scoped here. The differences need an explicit decision, not a quiet merge.

| Topic | April 2026 doc | This doc (Sept 2026) |
|---|---|---|
| Phase 1 focus | Move-in / freight elevator calendar and mass notifications | Equipment photo capture and annotation |
| Maintenance orders | Explicitly out of scope ("handled via 3CX or web") | In scope for supers |
| Elevator calendar | Phase 1 core feature with approval workflow | Explicitly cut from v1 |
| Tenant as app user | Yes, with own tab set, slot requests, notifications | Not a mobile user in v1 |
| Owner as app user | Not mentioned | Yes, with approval inbox |
| Shell | Native (Expo push, refresh token in SecureStore) | PWA first, Capacitor later |
| Push | FCM and APNs via Expo | Web Push via VAPID, APNs/FCM only after Capacitor wrap |
| Mass notifications | Phase 1 feature with full spec | Not in scope |
| Incident logging | Phase 1 feature | Not in scope (closest analog is MO with photo) |
| Vendor scheduling and COI | Phase 1 feature | Not in scope |

The April doc's feature specs for the elevator calendar and mass notifications are detailed and usable. If either comes back into scope, they should be lifted as-is rather than rewritten.

**Recommendation:** treat the September scope as current and the April doc as a backlog of well-specified phase-2 candidates. Elevator calendar and mass notifications are the two most likely to return, since both were explicitly confirmed with Manny in April.

---

## Risks

- **Super role is view-only** — the whole super workflow is blocked until the main app grants scoped write access. Resolve in phase 0 or nothing in phase 1 ships.
- **Maintenance orders may not exist in the main app** — if there is no MO entity, phase 2 needs a main-app workstream first.
- **Two mobile designs exist** — the April 2026 doc and this one disagree on scope, shell, and users. Pick one explicitly before any code is written.
- **iOS Web Push reliability** — the single biggest variable. Drives the Capacitor wrap decision and may force it earlier than planned.
- **Super location tracking → labor / legal exposure** if rolled out without the consent and disclosure flow. Don't let this ship without sign-off from whoever handles labor policy at propglue.
- **OCR quality variance** — receipts and invoices are easier than handwritten forms. Set expectations on which document types are supported; refuse silent failures.
- **Offline conflicts on equipment edits** — last-write-wins is the default but needs UI to surface overwrites. Don't pretend conflicts can't happen.
- **Cache scope explosion** — a PM with 200 buildings shouldn't sync 200 buildings of equipment to their phone. Smart eviction and on-demand fetch.
- **Asset tag generation dependency** — if the main app doesn't have it, phase 1 stalls. Validate this first.
