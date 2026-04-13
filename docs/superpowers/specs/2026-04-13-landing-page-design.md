# Landing Page & Auth Redesign — Design Spec

**Date**: 2026-04-13
**Status**: Approved

## Overview

Redesign the SES landing page and login flow. The current `GuestDashboard` component runs inside the app's `Layout` wrapper (with sidebar), making it cramped and disconnected. The login page is a minimal card with no context. This spec replaces both with a full-width, immersive landing page and a split-layout login experience.

**Core message**: Continuous improvement in education through data-driven outcome tracking.

**Target audience**: Students, instructors, and department heads equally.

**Visual style**: Academic/professional — clean, modern, warm. Teal primary, slate secondary, violet accents. Inter + Geist Variable fonts. No gradients on backgrounds (solid colors or subtle patterns only).

## Architecture

### Route structure

- `/` — Landing page (no `Layout` wrapper, full-width)
- `/login` — Split-layout auth page (no `Layout` wrapper)
- `/student`, `/instructor`, `/head`, `/settings`, `/security` — Inside `Layout` (unchanged)

### Auth flow

- Unauthenticated users hitting `/` see the landing page
- Clicking "Sign In" navigates to `/login`
- `/login` renders a split layout: left panel with subtle academic illustration/pattern, right panel with the login form
- Authenticated users hitting `/` get redirected to their role dashboard (existing behavior via `Dashboard.tsx`)

### Navigation

**Landing page navbar** (sticky, transparent on hero → solid white on scroll):
- Logo ("SES") — links to `/`
- Section anchors: Features, How It Works, Roles
- CTA button: "Sign In" → `/login`
- Mobile: hamburger menu

**No footer navigation to external pages** (no blog, docs site).

## Page Sections

### 1. Hero

- Badge/pill: "Outcome-Based Assessment Platform" (teal background)
- Headline: "Drive Continuous Improvement in Education" (bold)
- Subheadline: "Track student achievement from Assessment → Learning Outcome → Program Outcome. Make data-driven decisions that improve teaching quality and program accreditation."
- Two CTAs: "Get Started" (primary, teal) and "See How It Works" (secondary outline)
- Mini browser-frame preview of the actual SES dashboard UI (static mockup in an iMac/browser chrome frame)

### 2. Features (3x2 grid)

Six feature cards, each with a Heroicon, title, and one-line description:

| Icon | Title | Description |
|------|-------|-------------|
| ChartBarIcon | Outcome Tracking | Map assessments to learning outcomes and program outcomes automatically. |
| ArrowTrendingUpIcon | Data-Driven Insights | Visual dashboards that reveal trends across courses, departments, and programs. |
| CheckBadgeIcon | Accreditation Ready | Generate reports that align with ABET and institutional accreditation standards. |
| UserGroupIcon | Multi-Role Access | Tailored views for students, instructors, and department heads — one system, three perspectives. |
| ClipboardDocumentListIcon | Assessment Management | Create, assign, and evaluate assessments with direct outcome alignment built in. |
| ArrowPathIcon | Continuous Improvement | Close the loop — use evaluation data to refine curriculum and teaching methods cycle over cycle. |

Section headline: "Everything you need to improve outcomes"
Section subtitle: "From assessment design to accreditation reports — one platform for the full cycle."

Background: `#f8fafc` (slate-50)

### 3. How It Works (with embedded demo)

Three-step flow:
1. **Assess** — Instructors create assessments aligned to learning outcomes
2. **Map** — Scores aggregate into learning outcome achievement levels
3. **Improve** — Program outcomes inform curriculum improvements

Below the steps: an embedded interactive demo showing the Assessment → LO → PO pipeline flow. Users can click through tabs or steps to see how data flows through the system. This is a lightweight React component (not an iframe) that simulates the mapping flow.

Section headline: "See how outcomes flow through your institution"
Section subtitle: "From individual assessments to program-level improvement"

### 4. Role-Based Sections

Three cards on a dark background (`slate-900`), one per role:

**Students** (teal accent):
- Course outcome breakdown
- Personal achievement tracking
- Visual progress dashboards
- CTA: "Explore student view →"

**Instructors** (violet accent):
- Assessment creation & LO mapping
- Class outcome analytics
- Student performance comparison
- CTA: "Explore instructor view →"

**Department Heads** (green accent):
- Program outcome dashboards
- Cross-course LO analysis
- Accreditation report generation
- CTA: "Explore head view →"

Each card has a Heroicon in a colored circle, role name, description, feature list with checkmarks, and "Explore [role] view →" link. The "Explore" links will trigger the embedded demo to show the respective role's dashboard.

Section headline: "One platform, three perspectives"
Section subtitle: "Each role gets a tailored experience"

### 5. Live Stats

Horizontal row of 4 metrics against a white background:

| Label | Source |
|-------|--------|
| Universities | API count |
| Departments | API count |
| Programs | API count |
| Courses | API count (displayed as "100+" if over threshold) |

These are fetched from the backend API on page load. Each stat uses the accent color matching its role section (teal, violet, green, slate).

### 6. Call to Action

Teal background (`primary-600`):
- Headline: "Ready to improve your program outcomes?"
- Subtitle: "Join your institution's evaluation system and start making data-informed decisions."
- CTA button: "Get Started" (white text on teal, or white button with teal text — final choice during implementation)

### 7. Footer

Dark background (`slate-900`):
- Logo + "Student Evaluation System"
- Brief description: "Outcome-based assessment platform for higher education."
- **Platform** column: Features, How It Works, Roles (anchor links to sections)
- **University** column: Universities, Departments, Programs (links to public pages)
- Bottom bar: © 2026 | Privacy | Terms

### 8. Login Page (Split Layout)

**Left panel** (50% width):
- Subtle academic illustration/pattern — geometric shapes or abstract campus motif in teal/slate tones on a light neutral background
- SES value proposition text over the illustration
- "Accreditation-ready" and "Data-driven" tags

**Right panel** (50% width):
- Clean white background
- "Welcome back" heading
- "Sign in to your account" subtitle
- Username and password fields (existing `Login.tsx` form)
- Error message area
- "Sign In" button (teal, full width)
- Demo accounts section at bottom (existing)

**Mobile**: Stack vertically — illustration on top, form below (or hide illustration on very small screens).

## Component Structure

```
src/features/landing/
├── pages/
│   ├── LandingPage.tsx          # Main landing page route component
│   └── LoginPage.tsx            # Split-layout login (replaces current Login.tsx)
├── components/
│   ├── Navbar.tsx               # Sticky nav with scroll-aware transparency
│   ├── HeroSection.tsx          # Hero with badge, headline, CTAs, browser-frame preview
│   ├── FeaturesSection.tsx      # 3x2 feature cards grid
│   ├── HowItWorksSection.tsx    # Three-step flow + interactive demo
│   ├── EmbeddedDemo.tsx         # Interactive Assessment → LO → PO flow demo
│   ├── RoleCardsSection.tsx     # Three role cards on dark background
│   ├── LiveStatsSection.tsx     # API-fetched metrics row
│   ├── CTASection.tsx           # Call to action section
│   └── Footer.tsx               # Landing page footer
```

- `LandingPage.tsx` renders sections in order and does NOT wrap in `Layout`
- `LoginPage.tsx` replaces the current `Login.tsx` — updates the route in `App.tsx`
- The existing `GuestDashboard.tsx` is removed
- The existing `Login.tsx` form logic is extracted/kept in `LoginPage.tsx`'s right panel

## API Integration

Live stats section fetches counts from the API. Use existing React Query setup:

- Endpoint: existing university/department/program/course list endpoints (head count from response metadata or a dedicated stats endpoint)
- If the API doesn't have a stats endpoint, create one: `GET /api/stats/` returning `{ universities: N, departments: N, programs: N, courses: N }`
- If no stats endpoint exists, query university/department/program/course list endpoints and count from response pagination metadata
- Fallback: show placeholder skeleton cards while loading, hide section gracefully if API fails

## Key Design Decisions

1. **In-SPA, not separate site** — Landing page lives in the React app, shares components and routing. No extra build step or deployment.
2. **No Layout wrapper** — Landing and login pages render full-width without the sidebar. Clean separation.
3. **No gradients** — Solid color backgrounds only. Teal, slate, violet as accents. Subtle patterns allowed.
4. **Heroicons, not emojis** — All icons use `@heroicons/react/24/outline` (already a dependency).
5. **Embedded interactive demo** — Built as a React component, not an iframe. Lightweight simulation of the Assessment → LO → PO flow.
6. **Live stats from API** — No hardcoded numbers. Fetched on mount with React Query.
7. **Split-layout login** — Illustration/pattern on left, form on right. No gradient background.
8. **Scroll-aware navbar** — Transparent over hero, solid white on scroll.

## Out of Scope

- Dark mode toggle on the landing page (the app supports it internally, but the landing page is light-only)
- Animated page transitions between landing and login
- External pages (blog, docs, pricing)
- SEO optimization / meta tags (can be added later)
- A/B testing infrastructure
