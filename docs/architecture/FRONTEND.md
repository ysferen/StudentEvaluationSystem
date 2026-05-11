# Frontend Architecture Guide

## Overview

The frontend is built with React 18, TypeScript, and Vite. It uses a feature-based architecture with shared components and utilities.

```text
frontend/src/
├── features/           # Feature-based modules (auth, dashboard, courses, settings)
│   ├── <feature>/
│   │   ├── pages/      # Page components (route destinations)
│   │   ├── components/ # Feature-specific components
│   │   ├── hooks/      # Feature-specific hooks
│   │   └── index.ts    # Public API export
├── shared/
│   ├── api/           # Generated API clients
│   ├── components/   # Shared UI components
│   ├── hooks/        # Shared hooks
│   └── utils/        # Utility functions
├── components/
│   └── ui/           # shadcn/ui components (buttons, dialogs, forms, etc.)
└── App.tsx           # Route configuration
```

## How to Add a New Page

### Step 1: Create the Page Component

Create a new file in `frontend/src/features/<feature>/pages/`:

```tsx
// frontend/src/features/example/pages/ExamplePage.tsx
import { useQuery } from '@tanstack/react-query'
import { exampleApiGet } from '@/shared/api/generated/example/example'

export default function ExamplePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['example'],
    queryFn: () => exampleApiGet()
  })

  if (isLoading) return <div>Loading...</div>

  return <div>{data?.name}</div>
}
```

### Step 2: Export the Page

Add export in `frontend/src/features/example/index.ts`:

```ts
export { default as ExamplePage } from './pages/ExamplePage'
```

### Step 3: Wire the Route

Update `frontend/src/App.tsx`:

```tsx
const ExamplePage = lazy(() => import('./features/example/pages/ExamplePage'))

// Add route:
<Route path="/example" element={<Layout />}>
  <Route index element={<ExamplePage />} />
</Route>
```

### Step 4: Add Navigation (if needed)

Update the Sidebar component in `frontend/src/shared/components/Sidebar.tsx` to include the new route.

## Component Conventions

### Naming

- **Components**: PascalCase (`ExampleComponent.tsx`)
- **Hooks**: camelCase with `use` prefix (`useAuth.ts`)
- **Utils**: PascalCase for classes, camelCase for functions
- **Types/Interfaces**: PascalCase, suffix with `Props`, `Data`, etc.

### File Structure

```text
features/
└── example/
    ├── pages/
    │   ├── ExamplePage.tsx      # Main page
    │   └── ExampleDetail.tsx   # Detail page
    ├── components/
    │   ├── ExampleCard.tsx    # Reusable within feature
    │   └── index.ts           # Export all components
    ├── hooks/
    │   ├── useExample.ts      # Custom hook
    │   └── index.ts           # Export all hooks
    └── index.ts               # Feature public API
```

### Component Patterns

1. **Use TypeScript interfaces** for props
2. **Use React.FC or function component** syntax (both accepted)
3. **Extract complex logic** into custom hooks
4. **Use shadcn/ui components** for common UI patterns
5. **Use the Card component** for content containers

### API Integration

Use Orval-generated API clients:

```tsx
import { coreCoursesList } from '@/shared/api/generated/core/core'

// In component:
const { data } = useQuery({
  queryKey: ['courses'],
  queryFn: () => coreCoursesList().then(res => res.results)
})
```

### Styling

- Use Tailwind CSS classes
- Use existing color tokens: `primary-*`, `secondary-*`, `success-*`, `warning-*`, `danger-*`
- Use `clsx` for conditional classes
- Keep custom styles minimal; prefer component composition

## UI Components Reference

### shadcn/ui Components (Recommended)

Located in `frontend/src/components/ui/`:

| Component | Use For |
| ----------- | --------- |
| `Button` | Actions, form submissions, CTAs |
| `Input` | Text fields, form inputs |
| `Select` | Dropdown selections |
| `Dialog` | Modal dialogs, confirmations |
| `Form` | Complex forms with validation |
| `Card` | Content containers |

**Adding new shadcn components:**

```bash
cd frontend
npx shadcn@latest add <component-name>
```

### Custom UI Components

Located in `frontend/src/shared/components/ui/`:

| Component | Use For |
| ----------- | --------- |
| `Card` | Content containers with variants (default, hover, glass, flat) |
| `Badge` | Status indicators, labels |
| `Modal` | Simple modal dialogs |
| `ChartWidget` | Data visualization (ApexCharts) |
| `LazyChartWidget` | Lazy-loaded charts |
| `LoadingSkeleton` | Loading states |
| `Sidebar` | Navigation sidebar |
| `Header` | Top navigation bar |
| `Layout` | Page layout wrapper |

### Using shadcn with Custom Components

You can combine shadcn with custom components:

```tsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/shared/components/ui/Badge'

export function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Title</CardTitle>
        <Badge variant="success">Active</Badge>
      </CardHeader>
      <CardContent>
        <Button>Action</Button>
      </CardContent>
    </Card>
  )
}
```

## Testing

### Test Files

Tests are located in `frontend/src/test/` and use Vitest with React Testing Library.

```bash
# Run tests
npm run test

# Run with UI
npm run test:ui

# Coverage
npm run test:coverage
```

### Test Conventions

- File naming: `*.test.tsx` or `*.spec.tsx`
- Test location: Same as source or in `test/` folder
- Use MSW for API mocking (see `test/mocks/`)

## Available Scripts

```bash
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # Lint code
npm run test         # Run tests
npm run generate:api # Regenerate API clients
```

## API Client Generation

When backend API changes, regenerate frontend clients:

```bash
cd frontend
npm run generate:api
```

This updates `frontend/src/shared/api/generated/` from the OpenAPI schema.

## UI Design System

This project follows a consistent design language established by the landing page. All new UI components, dashboards, and modals must follow these patterns.

### Color Palette

The project uses three main color scales plus contextual accent colors:

| Scale | Usage | Key Values |
|-------|-------|------------|
| **primary** (teal) | CTAs, active states, brand identity | 50: `#f0fdfa` → 900: `#134e4a`, 600: `#0d9488` (default) |
| **secondary** (gray-blue) | Surfaces, text, borders, backgrounds | 50: `#f8fafc` → 900: `#0f172a`, 900 for dark sections, 50 for page backgrounds |
| **violet** | Secondary accent, instructor features, highlights | 500: `#a855f7`, 600: `#7c3aed` |
| **success** | Positive feedback | 500: `#22c55e`, 600: `#16a34a` |
| **warning** | Caution states | 500: `#f59e0b`, 600: `#d97706` |
| **danger** | Error/destructive states | 500: `#ef4444`, 600: `#dc2626` |

Accent pairing convention:
- primary → student-facing features
- violet → instructor features
- green → department head/admin features
- amber/orange → warnings and trend indicators

### Typography

- Font: `Inter, system-ui, sans-serif` (set in tailwind.config.js)
- Headings: `font-bold`, scale from `text-lg` (cards) → `text-4xl`/`text-6xl` (hero)
- Body: `text-sm` to `text-lg`, `text-secondary-500` for muted, `text-secondary-600` for secondary
- Labels: `text-xs uppercase tracking-wide` for small labels above values
- Stats: `text-3xl font-bold text-secondary-900` for large numbers

### Layout & Spacing

- Max content width: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- Section padding: `py-20 sm:py-28` (landing), `p-6` (dashboard cards)
- Grid layouts: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8`
- Card padding: `p-6 sm:p-8`
- Inter-element spacing: `space-y-6` or `space-y-8` for section-level, `gap-6` for grids

### Card Patterns

Use the `Card` component from `shared/components/ui/Card`:

- **default**: `bg-white shadow-card border border-secondary-200 rounded-xl` — standard cards
- **hover**: Same as default + `hover:shadow-card-hover hover:-translate-y-0.5` — interactive cards
- **flat**: `bg-white border border-secondary-200 rounded-xl` — no shadow
- **glass**: `bg-white/70 backdrop-blur-lg border border-white/20 shadow-lg` — overlay cards

Card with icon badge pattern:
```
<div className="h-12 w-12 rounded-xl {accent-bg} flex items-center justify-center mb-5">
  <Icon className="h-6 w-6 {accent-icon}" />
</div>
<h3 className="text-lg font-bold text-secondary-900 mb-2">{title}</h3>
<p className="text-secondary-500 text-sm leading-relaxed">{description}</p>
```

### Stat Card Pattern (from HeadDashboard)

For displaying key metrics:
```tsx
<Card variant="flat" className="bg-white border-secondary-200">
  <div className="flex items-center space-x-4">
    <div className="p-3 {accent-bg} rounded-xl">
      <Icon className="h-8 w-8 {accent-text}" />
    </div>
    <div>
      <p className="text-sm text-secondary-600 font-medium">{label}</p>
      <p className="text-3xl font-bold text-secondary-900">{value}</p>
    </div>
  </div>
</Card>
```

### Section Structure

Landing page section pattern:
```tsx
<section className="py-20 sm:py-28 {bg-class}">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="text-center mb-16">
      <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
        {heading}
      </h2>
      <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
        {subtitle}
      </p>
    </div>
    {/* Content */}
  </div>
</section>
```

Background alternation for landing sections: white → secondary-50 → white → secondary-900 → white → primary-600

Dashboard section pattern:
```tsx
<main className="p-6 max-w-7xl mx-auto">
  {/* Content */}
</main>
```

### Button Styles

| Role | Classes |
|------|---------|
| **Primary CTA** | `px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200` |
| **Secondary CTA** | `px-8 py-3.5 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200` (on dark bg) |
| **Small action** | `flex items-center gap-2 px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors` |
| **Tab toggle** | `px-3 py-1.5 text-sm rounded-lg transition {active ? 'bg-primary-600 text-white' : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'}` |
| **Ghost/Nav** | `text-sm font-medium text-secondary-600 hover:text-primary-600 transition-colors` |

### Modal Pattern

Modals use `fixed inset-0 z-50` overlay with centered content:
- Overlay: `bg-black bg-opacity-50` (or `bg-secondary-900/50 backdrop-blur-sm` for more polish)
- Container: `bg-white rounded-2xl shadow-xl w-full max-w-2xl relative`
- Header: `flex items-center justify-between p-6 border-b border-secondary-200`
- Body: `p-6 max-h-[70vh] overflow-y-auto`
- Close button: top-right X icon with `text-secondary-400 hover:text-secondary-600 transition-colors`

### Form Input Pattern

- Label: `block text-sm font-medium text-secondary-700 mb-2`
- Text input: `block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition`
- File input: custom styled with `file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100`

### Feedback/Alert Patterns

| Type | Classes |
|------|---------|
| **Success** | `bg-emerald-50 border border-emerald-200 rounded-xl p-6` with `text-emerald-800` heading, `text-emerald-600` body |
| **Error** | `bg-danger-50 border border-danger-200 rounded-xl p-6` with `text-danger-800` heading, `text-danger-600` body |
| **Warning** | `bg-warning-50 border border-warning-200 rounded-xl p-6` with `text-warning-800` heading |
| **Info** | `bg-primary-50 border border-primary-200 rounded-xl p-4` with `text-primary-800` heading, `text-primary-700` body |

Dismiss pattern:
```tsx
<button className="mt-4 px-4 py-2 bg-{color}-600 text-white rounded-lg hover:bg-{color}-700 transition-colors">
  Dismiss
</button>
```

### Loading & Empty States

Loading spinner:
```tsx
<div className="flex items-center justify-center h-96">
  <div className="text-center">
    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
    <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
  </div>
</div>
```

Skeleton loading (for inline):
```tsx
<div className="h-10 w-16 bg-secondary-200 rounded animate-pulse mx-auto mb-2" />
<div className="h-4 w-20 bg-secondary-100 rounded animate-pulse mx-auto" />
```

Empty state:
```tsx
<Card className="text-center py-12">
  <Icon className="h-12 w-12 mx-auto mb-4 text-secondary-300" />
  <h3 className="text-lg font-semibold text-secondary-900 mb-2">{title}</h3>
  <p className="text-secondary-500">{description}</p>
</Card>
```

### Step/Process Indicator Pattern

From HowItWorksSection: numbered circles with color coding:
```tsx
<div className={`w-10 h-10 ${color} text-white rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-lg`}>
  {number}
</div>
```

### Dark Section Pattern (from RoleCardsSection, Footer)

For hero-scale and footer sections:
- Background: `bg-secondary-900`
- Text colors: headings `text-white`, body `text-secondary-400`, links `text-secondary-300 hover:text-primary-400`
- Cards on dark: `bg-secondary-800 rounded-xl border border-{accent}-600/20`
- Dividers: `border-t border-secondary-700`

### Icon Box Pattern

For feature cards and stat cards:
```tsx
<div className="h-12 w-12 rounded-xl {accent-bg-color} flex items-center justify-center">
  <Icon className="h-6 w-6 {accent-icon-color}" />
</div>
```

Size variants: `h-10 w-10 rounded-lg` (compact), `h-12 w-12 rounded-xl` (default), `p-3 rounded-xl` (stat cards with larger icons `h-8 w-8`)

### Animation & Transitions

- Card hover: `hover:shadow-lg hover:-translate-y-1 transition-all duration-300`
- Button hover: `hover:-translate-y-0.5 hover:shadow-xl transition-all duration-200`
- Link/nav: `transition-colors duration-300`
- Navbar scroll: `transition-all duration-300`

### Responsive Breakpoints

- Mobile first approach
- Key breakpoints: `sm:`, `md:`, `lg:`
- Section padding: `py-20 sm:py-28`, `px-4 sm:px-6 lg:px-8`
- Grid: 1 col → `md:grid-cols-2` → `lg:grid-cols-3` (or `-4` for stats)
- Font scaling: `text-3xl sm:text-4xl lg:text-6xl` (hero), `text-xl sm:text-4xl` (section headings)
