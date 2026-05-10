# Landing Page & Auth Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Subagent assignment:** Use minimax subagents for implementation:
> - `minimax-builder` — Component code, wiring, routing (all implementation Task 1–10)
> - `minimax-styler` — Tailwind styling, animations, responsive polish (Task 11)
> - `minimax-tester` — Unit and integration tests (Task 12)

**Goal:** Replace the current GuestDashboard and Login page with a full-width landing page and split-layout auth experience.

**Architecture:** In-SPA approach — landing page and login are React routes that skip the Layout wrapper. The landing page is a scrollable single-page with 7 sections. Login is a split-layout with illustration/pattern on the left, form on the right. Existing Layout-wrapped routes are untouched.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS 3, shadcn/ui, @heroicons/react, @tanstack/react-query, react-router-dom v6

---

## File Structure

**Create:**
- `src/features/landing/pages/LandingPage.tsx` — Main landing page route component
- `src/features/landing/pages/LoginPage.tsx` — Split-layout login (replaces current Login.tsx)
- `src/features/landing/components/Navbar.tsx` — Sticky nav with scroll-aware transparency
- `src/features/landing/components/HeroSection.tsx` — Hero with badge, headline, CTAs, browser-frame preview
- `src/features/landing/components/FeaturesSection.tsx` — 3x2 feature cards grid
- `src/features/landing/components/HowItWorksSection.tsx` — Three-step flow
- `src/features/landing/components/EmbeddedDemo.tsx` — Interactive Assessment → LO → PO flow demo
- `src/features/landing/components/RoleCardsSection.tsx` — Three role cards on dark background
- `src/features/landing/components/LiveStatsSection.tsx` — API-fetched metrics row
- `src/features/landing/components/CTASection.tsx` — Call to action section
- `src/features/landing/components/Footer.tsx` — Landing page footer
- `src/features/landing/components/LoginIllustration.tsx` — Left panel SVG/pattern for login
- `src/features/landing/hooks/useLandingStats.ts` — React Query hook for live stats
- `src/features/landing/index.ts` — Feature barrel export

**Modify:**
- `src/App.tsx` — Add landing and login routes outside Layout, remove GuestDashboard import
- `src/features/auth/pages/Login.tsx` — Remove (replaced by LoginPage.tsx)
- `src/features/auth/index.ts` — Update exports
- `src/features/dashboard/pages/Dashboard.tsx` — Remove GuestDashboard import/redirect
- `src/features/dashboard/pages/GuestDashboard.tsx` — Remove

**Test:**
- `src/test/landing/` — Test directory for landing page tests

---

### Task 1: Create landing feature directory and barrel export

**Files:**
- Create: `src/features/landing/index.ts`

- [ ] **Step 1: Create the landing feature directory and barrel export**

```typescript
export { default as LandingPage } from './pages/LandingPage'
export { default as LoginPage } from './pages/LoginPage'
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/index.ts
git commit -m "feat(landing): add landing feature directory and barrel export"
```

---

### Task 2: Create Navbar component

**Files:**
- Create: `src/features/landing/components/Navbar.tsx`

This is a sticky navbar that is transparent when over the hero section and transitions to solid white on scroll. Links: Logo ("SES"), Features, How It Works, Roles (anchor links), Sign In button (routes to `/login`).

- [ ] **Step 1: Create Navbar.tsx**

```tsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
]

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white shadow-sm border-b border-secondary-200'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span
              className={`font-bold text-lg transition-colors duration-300 ${
                scrolled ? 'text-secondary-900' : 'text-white'
              }`}
            >
              SES
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors duration-300 hover:text-primary-600 ${
                  scrolled ? 'text-secondary-600' : 'text-white/80'
                }`}
              >
                {link.label}
              </a>
            ))}
            <Link
              to="/login"
              className="px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-lg hover:bg-primary-700 transition-colors"
            >
              Sign In
            </Link>
          </div>

          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            <div className="space-y-1.5">
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
            </div>
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-secondary-200 shadow-lg">
          <div className="px-4 py-4 space-y-3">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="block text-secondary-700 hover:text-primary-600 font-medium text-sm"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <Link
              to="/login"
              className="block text-center px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-lg hover:bg-primary-700 transition-colors"
              onClick={() => setMobileOpen(false)}
            >
              Sign In
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

export default Navbar
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/components/Navbar.tsx
git commit -m "feat(landing): add Navbar component with scroll-aware transparency"
```

---

### Task 3: Create HeroSection component

**Files:**
- Create: `src/features/landing/components/HeroSection.tsx`

- [ ] **Step 1: Create HeroSection.tsx**

```tsx
import { Link } from 'react-router-dom'

const HeroSection = () => {
  return (
    <section className="relative bg-secondary-900 overflow-hidden">
      {/* Subtle pattern overlay */}
      <div className="absolute inset-0 opacity-5">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25% 25%, rgba(13,148,136,0.3) 0%, transparent 50%), radial-gradient(circle at 75% 75%, rgba(124,58,237,0.2) 0%, transparent 50%)',
          }}
        />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20 sm:pt-40 sm:pb-28">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-1.5 bg-primary-100 text-primary-700 rounded-full text-sm font-semibold mb-6">
            Outcome-Based Assessment Platform
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight mb-6">
            Drive Continuous Improvement{' '}
            <span className="text-primary-400">in Education</span>
          </h1>

          {/* Subheadline */}
          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-secondary-300 mb-10 leading-relaxed">
            Track student achievement from Assessment → Learning Outcome → Program
            Outcome. Make data-driven decisions that improve teaching quality and program
            accreditation.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              to="/login"
              className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started
            </Link>
            <a
              href="#how-it-works"
              className="px-8 py-3.5 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200"
            >
              See How It Works
            </a>
          </div>

          {/* Browser-frame preview */}
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-secondary-200">
              {/* Browser chrome */}
              <div className="bg-secondary-100 px-4 py-2.5 flex items-center gap-2 border-b border-secondary-200">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <div className="flex-1 mx-4">
                  <div className="bg-white rounded-md px-3 py-1 text-xs text-secondary-400 text-center max-w-xs mx-auto">
                    ses.example.edu
                  </div>
                </div>
              </div>
              {/* Dashboard preview placeholder */}
              <div className="p-4 sm:p-6 bg-secondary-50">
                <div className="flex gap-4 sm:gap-6">
                  <div className="hidden sm:block w-36 bg-white rounded-lg border border-secondary-200 p-3 space-y-2">
                    <div className="text-primary-600 font-semibold text-xs">Navigation</div>
                    <div className="h-2 bg-secondary-200 rounded w-full" />
                    <div className="h-2 bg-secondary-200 rounded w-3/4" />
                    <div className="h-2 bg-secondary-200 rounded w-5/6" />
                  </div>
                  <div className="flex-1 space-y-3 sm:space-y-4">
                    <div className="font-semibold text-secondary-900 text-sm">
                      Course Outcomes Overview
                    </div>
                    <div className="grid grid-cols-3 gap-2 sm:gap-3">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-green-700 font-bold text-lg sm:text-xl">87%</div>
                        <div className="text-secondary-500 text-xs">LO Avg</div>
                      </div>
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-amber-700 font-bold text-lg sm:text-xl">72%</div>
                        <div className="text-secondary-500 text-xs">PO Avg</div>
                      </div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-blue-700 font-bold text-lg sm:text-xl">24</div>
                        <div className="text-secondary-500 text-xs">Students</div>
                      </div>
                    </div>
                    <div className="bg-white rounded-lg border border-secondary-200 p-3 flex items-end gap-1 h-16">
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '60%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '80%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '45%' }} />
                      <div className="flex-1 bg-primary-600 rounded-sm" style={{ height: '90%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '70%' }} />
                      <div className="flex-1 bg-primary-400 rounded-sm" style={{ height: '55%' }} />
                      <div className="flex-1 bg-primary-300 rounded-sm" style={{ height: '40%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default HeroSection
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/components/HeroSection.tsx
git commit -m "feat(landing): add HeroSection with browser-frame preview"
```

---

### Task 4: Create FeaturesSection component

**Files:**
- Create: `src/features/landing/components/FeaturesSection.tsx`

- [ ] **Step 1: Create FeaturesSection.tsx**

```tsx
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CheckBadgeIcon,
  UserGroupIcon,
  ClipboardDocumentListIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

const features = [
  {
    icon: ChartBarIcon,
    title: 'Outcome Tracking',
    description: 'Map assessments to learning outcomes and program outcomes automatically.',
    accent: 'primary',
  },
  {
    icon: ArrowTrendingUpIcon,
    title: 'Data-Driven Insights',
    description: 'Visual dashboards that reveal trends across courses, departments, and programs.',
    accent: 'amber',
  },
  {
    icon: CheckBadgeIcon,
    title: 'Accreditation Ready',
    description: 'Generate reports that align with ABET and institutional accreditation standards.',
    accent: 'blue',
  },
  {
    icon: UserGroupIcon,
    title: 'Multi-Role Access',
    description: 'Tailored views for students, instructors, and department heads — one system, three perspectives.',
    accent: 'pink',
  },
  {
    icon: ClipboardDocumentListIcon,
    title: 'Assessment Management',
    description: 'Create, assign, and evaluate assessments with direct outcome alignment built in.',
    accent: 'violet',
  },
  {
    icon: ArrowPathIcon,
    title: 'Continuous Improvement',
    description: 'Close the loop — use evaluation data to refine curriculum and teaching methods cycle over cycle.',
    accent: 'green',
  },
]

const accentStyles: Record<string, { bg: string; icon: string }> = {
  primary: { bg: 'bg-primary-100', icon: 'text-primary-600' },
  amber: { bg: 'bg-amber-100', icon: 'text-amber-600' },
  blue: { bg: 'bg-blue-100', icon: 'text-blue-600' },
  pink: { bg: 'bg-pink-100', icon: 'text-pink-600' },
  violet: { bg: 'bg-violet-100', icon: 'text-violet-600' },
  green: { bg: 'bg-green-100', icon: 'text-green-600' },
}

const FeaturesSection = () => {
  return (
    <section id="features" className="py-20 sm:py-28 bg-secondary-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
            Everything you need to improve outcomes
          </h2>
          <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
            From assessment design to accreditation reports — one platform for the full cycle.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {features.map(({ icon: Icon, title, description, accent }) => (
            <div
              key={title}
              className="bg-white rounded-xl border border-secondary-200 p-6 sm:p-8 hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
            >
              <div
                className={`h-12 w-12 rounded-xl ${accentStyles[accent].bg} flex items-center justify-center mb-5`}
              >
                <Icon className={`h-6 w-6 ${accentStyles[accent].icon}`} />
              </div>
              <h3 className="text-lg font-bold text-secondary-900 mb-2">{title}</h3>
              <p className="text-secondary-500 text-sm leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/components/FeaturesSection.tsx
git commit -m "feat(landing): add FeaturesSection with Heroicon-based cards"
```

---

### Task 5: Create EmbeddedDemo and HowItWorksSection components

**Files:**
- Create: `src/features/landing/components/EmbeddedDemo.tsx`
- Create: `src/features/landing/components/HowItWorksSection.tsx`

- [ ] **Step 1: Create EmbeddedDemo.tsx**

This is an interactive component showing the Assessment → LO → PO mapping flow. Users click through tabs to see how data flows. It simulates three views: the Assessment, the LO aggregation, and the PO result.

```tsx
import { useState } from 'react'

type DemoStep = 'assessment' | 'lo' | 'po'

const STEPS: { key: DemoStep; label: string; color: string }[] = [
  { key: 'assessment', label: 'Midterm Exam', color: 'primary' },
  { key: 'lo', label: 'LO 3.2', color: 'violet' },
  { key: 'po', label: 'PO 1', color: 'green' },
]

const ASSESSMENT_DATA = [
  { student: 'Ahmet Y.', score: 85, status: 'Complete' },
  { student: 'Elif K.', score: 72, status: 'Complete' },
  { student: 'Mehmet A.', score: 91, status: 'Complete' },
  { student: 'Zeynep D.', score: 68, status: 'Complete' },
]

const LO_DATA = { name: 'LO 3.2', description: 'Apply statistical methods to engineering problems', average: '79%', target: '70%', status: 'Met' }

const PO_DATA = { name: 'PO 1', description: 'Engineering knowledge and problem analysis', mappedLOs: 4, averageScore: '76%', status: 'On Track' }

const colorMap: Record<string, { bg: string; text: string; badge: string; bar: string }> = {
  primary: { bg: 'bg-primary-50', text: 'text-primary-700', badge: 'bg-primary-100 text-primary-700', bar: 'bg-primary-500' },
  violet: { bg: 'bg-violet-50', text: 'text-violet-700', badge: 'bg-violet-100 text-violet-700', bar: 'bg-violet-500' },
  green: { bg: 'bg-green-50', text: 'text-green-700', badge: 'bg-green-100 text-green-700', bar: 'bg-green-500' },
}

const EmbeddedDemo = () => {
  const [activeStep, setActiveStep] = useState<DemoStep>('assessment')

  return (
    <div className="bg-secondary-50 rounded-xl border border-secondary-200 overflow-hidden">
      <div className="px-4 py-2 text-xs text-secondary-400 text-center border-b border-secondary-200">
        ← Interactive demo — click through the flow →
      </div>

      {/* Step selector */}
      <div className="flex items-center justify-center gap-2 sm:gap-3 px-4 py-3 bg-white border-b border-secondary-200">
        {STEPS.map((step, i) => (
          <button
            key={step.key}
            onClick={() => setActiveStep(step.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-colors ${
              activeStep === step.key
                ? `${colorMap[step.color].badge}`
                : 'text-secondary-400 hover:text-secondary-600'
            }`}
          >
            <span className="w-5 h-5 rounded-full bg-current/[0.15] flex items-center justify-center text-[10px]">
              {i + 1}
            </span>
            {step.label}
            {i < STEPS.length - 1 && <span className="text-secondary-300 mx-1">→</span>}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="p-4 sm:p-6">
        {activeStep === 'assessment' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.primary.text}`}>Midterm Exam</span>
              <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full font-medium">Assessment</span>
            </div>
            <div className="space-y-2">
              {ASSESSMENT_DATA.map((row) => (
                <div key={row.student} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-secondary-200">
                  <span className="text-xs sm:text-sm text-secondary-700">{row.student}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs sm:text-sm font-semibold text-secondary-900">{row.score}</span>
                    <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded">{row.status}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Individual scores are collected and mapped…</p>
          </div>
        )}

        {activeStep === 'lo' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.violet.text}`}>{LO_DATA.name}</span>
              <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">Learning Outcome</span>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 p-3 sm:p-4 space-y-2">
              <p className="text-xs sm:text-sm text-secondary-600">{LO_DATA.description}</p>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-violet-700">{LO_DATA.average}</div>
                  <div className="text-[10px] text-secondary-500">Average</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-secondary-900">{LO_DATA.target}</div>
                  <div className="text-[10px] text-secondary-500">Target</div>
                </div>
                <div className="text-center">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">{LO_DATA.status}</span>
                </div>
              </div>
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Aggregated into program-level outcomes…</p>
          </div>
        )}

        {activeStep === 'po' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.green.text}`}>{PO_DATA.name}</span>
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Program Outcome</span>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 p-3 sm:p-4 space-y-2">
              <p className="text-xs sm:text-sm text-secondary-600">{PO_DATA.description}</p>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-700">{PO_DATA.mappedLOs}</div>
                  <div className="text-[10px] text-secondary-500">Mapped LOs</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-secondary-900">{PO_DATA.averageScore}</div>
                  <div className="text-[10px] text-secondary-500">Average</div>
                </div>
                <div className="text-center">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">{PO_DATA.status}</span>
                </div>
              </div>
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Data informs curriculum improvements → cycle repeats</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default EmbeddedDemo
```

- [ ] **Step 2: Create HowItWorksSection.tsx**

```tsx
import EmbeddedDemo from './EmbeddedDemo'

const STEPS_DATA = [
  {
    number: '1',
    title: 'Assess',
    description: 'Instructors create assessments aligned to learning outcomes',
    color: 'bg-primary-600',
  },
  {
    number: '2',
    title: 'Map',
    description: 'Scores aggregate into learning outcome achievement levels',
    color: 'bg-violet-600',
  },
  {
    number: '3',
    title: 'Improve',
    description: 'Program outcomes inform curriculum improvements',
    color: 'bg-green-600',
  },
]

const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
            See how outcomes flow through your institution
          </h2>
          <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
            From individual assessments to program-level improvement
          </p>
        </div>

        {/* Three steps */}
        <div className="flex flex-col sm:flex-row justify-center gap-8 sm:gap-16 mb-12">
          {STEPS_DATA.map(({ number, title, description, color }) => (
            <div key={number} className="text-center flex-1 max-w-[200px] mx-auto sm:mx-0">
              <div
                className={`w-10 h-10 ${color} text-white rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-lg`}
              >
                {number}
              </div>
              <h3 className="font-bold text-secondary-900 mb-1">{title}</h3>
              <p className="text-sm text-secondary-500">{description}</p>
            </div>
          ))}
        </div>

        {/* Embedded demo */}
        <EmbeddedDemo />
      </div>
    </section>
  )
}

export default HowItWorksSection
```

- [ ] **Step 3: Commit**

```bash
git add src/features/landing/components/EmbeddedDemo.tsx src/features/landing/components/HowItWorksSection.tsx
git commit -m "feat(landing): add HowItWorksSection with embedded interactive demo"
```

---

### Task 6: Create RoleCardsSection component

**Files:**
- Create: `src/features/landing/components/RoleCardsSection.tsx`

- [ ] **Step 1: Create RoleCardsSection.tsx**

```tsx
import {
  AcademicCapIcon,
  UserGroupIcon,
  BuildingLibraryIcon,
} from '@heroicons/react/24/outline'

const roles = [
  {
    icon: AcademicCapIcon,
    title: 'Students',
    description:
      'Track your progress across courses. See how each assessment contributes to your learning outcomes and where you stand.',
    features: ['Course outcome breakdown', 'Personal achievement tracking', 'Visual progress dashboards'],
    accent: 'primary',
    cta: 'Explore student view',
    href: '/login',
  },
  {
    icon: UserGroupIcon,
    title: 'Instructors',
    description:
      'Manage assessments and see how students perform against learning outcomes. Identify what\'s working and what\'s not.',
    features: ['Assessment creation & LO mapping', 'Class outcome analytics', 'Student performance comparison'],
    accent: 'violet',
    cta: 'Explore instructor view',
    href: '/login',
  },
  {
    icon: BuildingLibraryIcon,
    title: 'Department Heads',
    description:
      'Oversee program-level outcomes and generate accreditation reports. Make strategic decisions backed by real data.',
    features: ['Program outcome dashboards', 'Cross-course LO analysis', 'Accreditation report generation'],
    accent: 'green',
    cta: 'Explore head view',
    href: '/login',
  },
]

const accentMap: Record<string, { icon: string; bg: string; check: string; link: string; border: string }> = {
  primary: { icon: 'bg-primary-600', bg: 'bg-primary-100', check: 'text-primary-600', link: 'text-primary-500', border: 'border-primary-600/20' },
  violet: { icon: 'bg-violet-600', bg: 'bg-violet-100', check: 'text-violet-600', link: 'text-violet-500', border: 'border-violet-600/20' },
  green: { icon: 'bg-green-600', bg: 'bg-green-100', check: 'text-green-600', link: 'text-green-500', border: 'border-green-600/20' },
}

const RoleCardsSection = () => {
  return (
    <section id="roles" className="py-20 sm:py-28 bg-secondary-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            One platform, three perspectives
          </h2>
          <p className="text-lg text-secondary-400 max-w-2xl mx-auto">
            Each role gets a tailored experience
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {roles.map(({ icon: Icon, title, description, features, accent, cta, href }) => {
            const styles = accentMap[accent]
            return (
              <div
                key={title}
                className={`bg-secondary-800 rounded-xl p-6 sm:p-8 border ${styles.border} hover:border-opacity-60 transition-all duration-300`}
              >
                <div className={`w-12 h-12 rounded-xl ${styles.icon} flex items-center justify-center mb-4`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
                <p className="text-secondary-400 text-sm leading-relaxed mb-5">{description}</p>
                <ul className="space-y-2 mb-6">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-secondary-300 text-sm">
                      <span className={styles.check}>✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>
                <a
                  href={href}
                  className={`${styles.link} text-sm font-semibold hover:underline`}
                >
                  {cta} →
                </a>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default RoleCardsSection
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/components/RoleCardsSection.tsx
git commit -m "feat(landing): add RoleCardsSection with three role cards"
```

---

### Task 7: Create LiveStatsSection, CTASection, and Footer components

**Files:**
- Create: `src/features/landing/components/LiveStatsSection.tsx`
- Create: `src/features/landing/components/CTASection.tsx`
- Create: `src/features/landing/components/Footer.tsx`
- Create: `src/features/landing/hooks/useLandingStats.ts`

- [ ] **Step 1: Create useLandingStats.ts hook**

Uses React Query to fetch counts from the existing list endpoints. Each endpoint returns paginated results — we only need the `count` field from the pagination metadata. We request `page_size=1` to minimize payload.

```typescript
import { useQuery } from '@tanstack/react-query'
import { axiosInstance } from '../../../shared/api/mutator'

interface Stats {
  universities: number
  departments: number
  programs: number
  courses: number
}

export const useLandingStats = () => {
  return useQuery<Stats>({
    queryKey: ['landing-stats'],
    queryFn: async () => {
      const [universities, departments, programs, courses] = await Promise.all([
        axiosInstance.get('/api/core/universities/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/departments/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/programs/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/courses/', { params: { page_size: 1 } }).then((r) => r.data),
      ])

      return {
        universities: universities.count ?? 0,
        departments: departments.count ?? 0,
        programs: programs.count ?? 0,
        courses: courses.count ?? 0,
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
```

- [ ] **Step 2: Create LiveStatsSection.tsx**

```tsx
import { useLandingStats } from '../hooks/useLandingStats'

const stats = [
  { label: 'Universities', color: 'text-primary-600' },
  { label: 'Departments', color: 'text-violet-600' },
  { label: 'Programs', color: 'text-green-600' },
  { label: 'Courses', color: 'text-secondary-900' },
]

const LiveStatsSection = () => {
  const { data, isLoading } = useLandingStats()

  if (isLoading) {
    return (
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center gap-8 sm:gap-16">
            {stats.map(({ label }) => (
              <div key={label} className="text-center">
                <div className="h-10 w-16 bg-secondary-200 rounded animate-pulse mx-auto mb-2" />
                <div className="h-4 w-20 bg-secondary-100 rounded animate-pulse mx-auto" />
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (!data) return null

  const values = [data.universities, data.departments, data.programs, data.courses]

  return (
    <section className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-center gap-8 sm:gap-16">
          {stats.map(({ label, color }, i) => (
            <div key={label} className="text-center">
              <div className={`text-3xl sm:text-4xl font-bold ${color}`}>
                {values[i] >= 100 ? `${values[i]}+` : values[i]}
              </div>
              <div className="text-sm text-secondary-500 font-medium mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default LiveStatsSection
```

- [ ] **Step 3: Create CTASection.tsx**

```tsx
import { Link } from 'react-router-dom'

const CTASection = () => {
  return (
    <section className="bg-primary-600 py-20 sm:py-24">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
          Ready to improve your program outcomes?
        </h2>
        <p className="text-lg text-primary-100 mb-8 max-w-2xl mx-auto">
          Join your institution's evaluation system and start making data-informed decisions.
        </p>
        <Link
          to="/login"
          className="inline-block px-8 py-3.5 bg-white text-primary-600 font-bold rounded-xl shadow-lg hover:bg-primary-50 transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5"
        >
          Get Started
        </Link>
      </div>
    </section>
  )
}

export default CTASection
```

- [ ] **Step 4: Create Footer.tsx**

```tsx
import { Link } from 'react-router-dom'

const Footer = () => {
  return (
    <footer className="bg-secondary-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="flex flex-col md:flex-row justify-between gap-8 mb-8">
          <div className="max-w-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-7 w-7 bg-primary-600 rounded-md flex items-center justify-center">
                <span className="text-white font-bold text-xs">S</span>
              </div>
              <span className="font-bold text-base">Student Evaluation System</span>
            </div>
            <p className="text-secondary-400 text-sm leading-relaxed">
              Outcome-based assessment platform for higher education. Track achievement, improve teaching, meet accreditation standards.
            </p>
          </div>

          <div className="flex gap-16">
            <div>
              <h4 className="font-semibold text-sm text-secondary-200 mb-3">Platform</h4>
              <ul className="space-y-2">
                <li><a href="#features" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Features</a></li>
                <li><a href="#how-it-works" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">How It Works</a></li>
                <li><a href="#roles" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Roles</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm text-secondary-200 mb-3">University</h4>
              <ul className="space-y-2">
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Universities</Link></li>
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Departments</Link></li>
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Programs</Link></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="border-t border-secondary-700 pt-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-secondary-500 text-xs">&copy; 2026 Student Evaluation System</p>
          <div className="flex gap-6">
            <span className="text-secondary-500 text-xs hover:text-secondary-300 cursor-pointer">Privacy</span>
            <span className="text-secondary-500 text-xs hover:text-secondary-300 cursor-pointer">Terms</span>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
```

- [ ] **Step 5: Commit**

```bash
git add src/features/landing/components/LiveStatsSection.tsx src/features/landing/components/CTASection.tsx src/features/landing/components/Footer.tsx src/features/landing/hooks/useLandingStats.ts
git commit -m "feat(landing): add LiveStats, CTA, Footer, and useLandingStats hook"
```

---

### Task 8: Create LandingPage route component

**Files:**
- Create: `src/features/landing/pages/LandingPage.tsx`

This is the main route component that renders all sections in order. It does NOT use the Layout wrapper.

- [ ] **Step 1: Create LandingPage.tsx**

```tsx
import Navbar from '../components/Navbar'
import HeroSection from '../components/HeroSection'
import FeaturesSection from '../components/FeaturesSection'
import HowItWorksSection from '../components/HowItWorksSection'
import RoleCardsSection from '../components/RoleCardsSection'
import LiveStatsSection from '../components/LiveStatsSection'
import CTASection from '../components/CTASection'
import Footer from '../components/Footer'

const LandingPage = () => {
  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <RoleCardsSection />
      <LiveStatsSection />
      <CTASection />
      <Footer />
    </div>
  )
}

export default LandingPage
```

- [ ] **Step 2: Commit**

```bash
git add src/features/landing/pages/LandingPage.tsx
git commit -m "feat(landing): add LandingPage route component"
```

---

### Task 9: Create LoginPage (split-layout login)

**Files:**
- Create: `src/features/landing/components/LoginIllustration.tsx`
- Create: `src/features/landing/pages/LoginPage.tsx`

The left panel shows a subtle geometric/academic pattern. The right panel reuses the auth form logic from the existing `Login.tsx`.

- [ ] **Step 1: Create LoginIllustration.tsx**

Creates an SVG-based subtle academic pattern with teal/slate tones. Contains the SES branding and value proposition tags.

```tsx
import { Link } from 'react-router-dom'

const LoginIllustration = () => {
  return (
    <div className="hidden lg:flex lg:w-1/2 relative bg-secondary-50 overflow-hidden">
      {/* Geometric pattern */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <circle cx="20%" cy="30%" r="120" fill="#0d9488" opacity="0.08" />
        <circle cx="80%" cy="70%" r="90" fill="#7c3aed" opacity="0.06" />
        <circle cx="50%" cy="50%" r="60" fill="#0d9488" opacity="0.05" />
      </svg>

      <div className="relative z-10 flex flex-col justify-center px-12 xl:px-20">
        <Link to="/" className="flex items-center gap-3 mb-8">
          <div className="h-10 w-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">S</span>
          </div>
          <span className="font-bold text-xl text-secondary-900">SES</span>
        </Link>

        <h2 className="text-3xl xl:text-4xl font-bold text-secondary-900 mb-4 leading-tight">
          Student Evaluation<br />System
        </h2>
        <p className="text-secondary-500 mb-8 max-w-sm leading-relaxed">
          Track achievement from Assessment → Learning Outcome → Program Outcome
        </p>

        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center px-3 py-1.5 bg-primary-100 text-primary-700 text-sm font-medium rounded-full">
           .Accreditation-ready
          </span>
          <span className="inline-flex items-center px-3 py-1.5 bg-violet-100 text-violet-700 text-sm font-medium rounded-full">
            Data-driven
          </span>
        </div>
      </div>
    </div>
  )
}

export default LoginIllustration
```

Note: Remove the extra period before "Accreditation-ready" — that's a typo. The correct text is `Accreditation-ready`.

- [ ] **Step 2: Create LoginPage.tsx**

This component replicates the auth form logic from the existing `Login.tsx` but in a split layout. It does NOT import the old Login component.

```tsx
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../auth/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import LoginIllustration from '../components/LoginIllustration'

const LoginPage = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const { login, isAuthenticated, user } = useAuth()

  if (isAuthenticated && user) {
    const rolePath = user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : user.role === 'student' ? '/student' : '/'
    return <Navigate to={rolePath} replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(username, password)
    } catch (err: unknown) {
      const errObj = err as { response?: { data?: { message?: string } } }
      setError(errObj.response?.data?.message || 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      <LoginIllustration />

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-secondary-900 mb-1">Welcome back</h1>
          <p className="text-secondary-500 mb-8">Sign in to your account</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>

            {error && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 pt-4 border-t text-sm text-secondary-500">
            <p className="font-medium mb-2">Demo Accounts:</p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="font-semibold">Admin:</span>
                <br />
                admin / admin
              </div>
              <div>
                <span className="font-semibold">Lecturer:</span>
                <br />
                lecturer / lecturer
              </div>
              <div>
                <span className="font-semibold">Student:</span>
                <br />
                student / student
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
```

- [ ] **Step 3: Commit**

```bash
git add src/features/landing/components/LoginIllustration.tsx src/features/landing/pages/LoginPage.tsx
git commit -m "feat(landing): add split-layout LoginPage with illustration panel"
```

---

### Task 10: Update routes and remove old components

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/features/auth/index.ts`
- Modify: `src/features/dashboard/pages/Dashboard.tsx`
- Delete: `src/features/auth/pages/Login.tsx`
- Delete: `src/features/dashboard/pages/GuestDashboard.tsx`

- [ ] **Step 1: Update App.tsx routes**

Replace the `LoginPage` import and route, add `LandingPage` route outside Layout, and ensure the root `/` route works correctly.

In `src/App.tsx`, make these changes:
- Remove lazy import of `LoginPage` from auth
- Add lazy import of `LandingPage` from landing
- Add lazy import of `LoginPage` from landing
- Change the `/login` route to use the new `LoginPage`
- Change the `/` route: when NOT authenticated, show `LandingPage`; when authenticated, the existing `Dashboard` redirect logic applies

The updated `App.tsx` should look like this (showing only the changed lines):

```tsx
import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './shared/components'

const LandingPage = lazy(() => import('./features/landing/pages/LandingPage'))
const LoginPage = lazy(() => import('./features/landing/pages/LoginPage'))
const DashboardPage = lazy(() => import('./features/dashboard/pages/Dashboard'))
// ... keep all other lazy imports the same

function App() {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Student routes with shared layout */}
        <Route path="/student" element={<Layout showOnlyCoreItems={true} />}>
          <Route index element={<StudentDashboardPage />} />
          <Route path="courses" element={<StudentCoursesPage />} />
        </Route>
        {/* ... rest unchanged ... */}
      </Routes>
    </Suspense>
  )
}
```

Key changes: Remove the `<Layout>` wrapper from the `/` route. The `/` route now renders `LandingPage` without Layout. Authenticated user redirect is handled inside `LandingPage` (which checks `useAuth` and redirects).

Wait — `LandingPage` should NOT redirect authenticated users. The existing `Dashboard.tsx` handles that. But if we change `/` to `LandingPage`, authenticated users hitting `/` will see the landing page instead of their dashboard. We need to handle this.

The best approach: `/` shows `LandingPage` for unauthenticated users. Authenticated users visiting `/` should be redirected to their role dashboard. We keep `DashboardPage` logic but as a separate route or handle it in `LandingPage`.

Update `LandingPage` to check auth and redirect:

```tsx
import { useAuth } from '../../auth/hooks/useAuth'
import { Navigate } from 'react-router-dom'

const LandingPage = () => {
  const { isAuthenticated, user } = useAuth()

  if (isAuthenticated && user) {
    const rolePath = user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : user.role === 'student' ? '/student' : '/'
    return <Navigate to={rolePath} replace />
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      {/* ... sections ... */}
    </div>
  )
}
```

This means `Dashboard.tsx` no longer needs `GuestDashboard`. Update `Dashboard.tsx` to only handle authenticated redirects:

```tsx
import { useAuth } from '../../auth/hooks/useAuth'
import { Navigate } from 'react-router-dom'

const Dashboard = () => {
  const { user } = useAuth()

  if (!user) {
    return <Navigate to="/" replace />
  }

  const rolePath = user.role === 'student' ? '/student' : user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : '/login'
  return <Navigate to={rolePath} replace />
}

export default Dashboard
```

And update auth `index.ts` to remove the `LoginPage` export:

```typescript
// Auth feature exports
export { useAuth, AuthProvider } from './hooks/useAuth'
```

- [ ] **Step 2: Commit all route changes and deletions**

```bash
git add src/App.tsx src/features/auth/index.ts src/features/dashboard/pages/Dashboard.tsx src/features/landing/pages/LandingPage.tsx
git rm src/features/auth/pages/Login.tsx src/features/dashboard/pages/GuestDashboard.tsx
git commit -m "feat(landing): update routes, remove old Login and GuestDashboard, wire LandingPage and LoginPage"
```

---

### Task 11: Tailwind styling polish and responsive refinement

**Assigned to: minimax-styler**

**Files:**
- Modify: `src/features/landing/components/Navbar.tsx`
- Modify: `src/features/landing/components/HeroSection.tsx`
- Modify: `src/features/landing/pages/LoginPage.tsx`
- All other landing components

- [ ] **Step 1: Verify all landing page components render correctly**

Run `npm run dev` from the frontend directory and visually verify:
- Navbar scroll transparency transition works
- All sections render in correct order
- Mobile hamburger menu opens/closes
- Hero section browser-frame preview displays properly
- Feature cards grid collapses to 1 column on mobile
- Role cards grid collapses to 1 column on mobile
- Live stats row wraps on small screens
- Footer layout stacks on mobile
- Login page splits correctly on desktop, stacks on mobile

- [ ] **Step 2: Polish responsive breakpoints**

Ensure all components have proper responsive classes:
- `Navbar`: hamburger menu visible at `md:` breakpoint
- `HeroSection`: typography scales from `text-4xl` to `text-6xl`
- `FeaturesSection`: grid goes from `grid-cols-1` (mobile) to `md:grid-cols-2` to `lg:grid-cols-3`
- `RoleCardsSection`: grid goes from `grid-cols-1` to `md:grid-cols-3`
- `LoginIllustration`: `hidden lg:flex` to hide on smaller screens
- `LoginPage`: form panel `w-full lg:w-1/2`

- [ ] **Step 3: Add smooth scroll behavior**

In `src/index.css`, add to the `@layer base` block:

```css
html {
  scroll-behavior: smooth;
}
```

- [ ] **Step 4: Commit styling polish**

```bash
git add -u
git commit -m "style(landing): polish responsive breakpoints and smooth scroll"
```

---

### Task 12: Write tests

**Assigned to: minimax-tester**

**Files:**
- Create: `src/test/landing/LandingPage.test.tsx`
- Create: `src/test/landing/LoginPage.test.tsx`
- Create: `src/test/landing/Navbar.test.tsx`
- Create: `src/test/landing/LiveStatsSection.test.tsx`
- Create: `src/test/landing/EmbeddedDemo.test.tsx`

- [ ] **Step 1: Write LandingPage rendering test**

Test that LandingPage renders all sections and redirects authenticated users.

```tsx
// src/test/landing/LandingPage.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LandingPage from '../../features/landing/pages/LandingPage'

vi.mock('../../features/auth/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, isLoading: false }),
}))

const renderLanding = () =>
  render(
    <BrowserRouter>
      <LandingPage />
    </BrowserRouter>
  )

describe('LandingPage', () => {
  it('renders the navbar with Sign In link', () => {
    renderLanding()
    expect(screen.getByText('Sign In')).toBeInTheDocument()
  })

  it('renders the hero headline', () => {
    renderLanding()
    expect(screen.getByText(/Drive Continuous Improvement/)).toBeInTheDocument()
  })

  it('renders the features section', () => {
    renderLanding()
    expect(screen.getByText('Outcome Tracking')).toBeInTheDocument()
    expect(screen.getByText('Data-Driven Insights')).toBeInTheDocument()
  })

  it('renders the roles section', () => {
    renderLanding()
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Instructors')).toBeInTheDocument()
    expect(screen.getByText('Department Heads')).toBeInTheDocument()
  })

  it('renders the CTA section', () => {
    renderLanding()
    expect(screen.getByText(/Ready to improve/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Write LoginPage rendering test**

Test that LoginPage renders the split layout, form fields, and demo accounts.

```tsx
// src/test/landing/LoginPage.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '../../features/landing/pages/LoginPage'

vi.mock('../../features/auth/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, login: vi.fn(), isLoading: false }),
}))

const renderLogin = () =>
  render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  )

describe('LoginPage', () => {
  it('renders the welcome heading', () => {
    renderLogin()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
  })

  it('renders username and password fields', () => {
    renderLogin()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('renders the sign in button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders demo accounts', () => {
    renderLogin()
    expect(screen.getByText(/demo accounts/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Write Navbar test**

```tsx
// src/test/landing/Navbar.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Navbar from '../../features/landing/components/Navbar'

const renderNavbar = () =>
  render(
    <BrowserRouter>
      <Navbar />
    </BrowserRouter>
  )

describe('Navbar', () => {
  it('renders the SES logo', () => {
    renderNavbar()
    expect(screen.getByText('SES')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    renderNavbar()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Roles')).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderNavbar()
    expect(screen.getByText('Sign In')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Write EmbeddedDemo test**

```tsx
// src/test/landing/EmbeddedDemo.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EmbeddedDemo from '../../features/landing/components/EmbeddedDemo'

describe('EmbeddedDemo', () => {
  it('renders with assessment step visible by default', () => {
    render(<EmbeddedDemo />)
    expect(screen.getByText('Midterm Exam')).toBeInTheDocument()
  })

  it('switches to LO view when LO step is clicked', async () => {
    const user = userEvent.setup()
    render(<EmbeddedDemo />)
    await user.click(screen.getByText('LO 3.2'))
    expect(screen.getByText('Apply statistical methods to engineering problems')).toBeInTheDocument()
  })

  it('switches to PO view when PO step is clicked', async () => {
    const user = userEvent.setup()
    render(<EmbeddedDemo />)
    await user.click(screen.getByText('PO 1'))
    expect(screen.getByText('Engineering knowledge and problem analysis')).toBeInTheDocument()
  })
})
```

- [ ] **Step 5: Write LiveStatsSection test**

```tsx
// src/test/landing/LiveStatsSection.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import LiveStatsSection from '../../features/landing/components/LiveStatsSection'

vi.mock('../../features/landing/hooks/useLandingStats', () => ({
  useLandingStats: () => ({
    data: { universities: 2, departments: 8, programs: 15, courses: 104 },
    isLoading: false,
  }),
}))

describe('LiveStatsSection', () => {
  it('renders all stat labels', () => {
    render(<LiveStatsSection />)
    expect(screen.getByText('Universities')).toBeInTheDocument()
    expect(screen.getByText('Departments')).toBeInTheDocument()
    expect(screen.getByText('Programs')).toBeInTheDocument()
    expect(screen.getByText('Courses')).toBeInTheDocument()
  })

  it('displays 100+ for courses over threshold', () => {
    render(<LiveStatsSection />)
    expect(screen.getByText('100+')).toBeInTheDocument()
  })
})
```

- [ ] **Step 6: Run all landing page tests**

```bash
cd frontend && npm run test -- --run src/test/landing/
```

Expected: All tests pass.

- [ ] **Step 7: Run full test suite and lint**

```bash
cd frontend && npm run lint && npm run test -- --run
```

Expected: All pass, no regressions.

- [ ] **Step 8: Commit tests**

```bash
git add src/test/landing/
git commit -m "test(landing): add tests for LandingPage, LoginPage, Navbar, EmbeddedDemo, LiveStatsSection"
```

---

### Task 13: Final integration and build verification

**Files:**
- All landing feature files

- [ ] **Step 1: Run the full build to verify no TypeScript errors**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Run lint to verify no linting errors**

```bash
cd frontend && npm run lint
```

Expected: No errors.

- [ ] **Step 3: Run the full test suite**

```bash
cd frontend && npm run test -- --run
```

Expected: All tests pass.

- [ ] **Step 4: Visually verify in the browser**

Start the dev server and check:
1. `http://localhost:5173/` shows the landing page with all sections
2. Clicking "Sign In" navigates to `/login` with split layout
3. Login with demo accounts works and redirects to role dashboards
4. Already-authenticated users visiting `/` redirect to their dashboard
5. Navbar links scroll to correct sections
6. Mobile responsive layout works at 375px, 768px, and 1280px widths

- [ ] **Step 5: Commit final integration verification**

If any fixes were needed during verification, commit them:

```bash
git add -u && git commit -m "fix(landing): address integration issues from build verification"
```
