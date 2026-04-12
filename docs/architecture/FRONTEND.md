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
