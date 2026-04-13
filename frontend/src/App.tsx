import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './shared/components'

const LandingPage = lazy(() => import('./features/landing/pages/LandingPage'))
const LoginPage = lazy(() => import('./features/landing/pages/LoginPage'))
const DashboardPage = lazy(() => import('./features/dashboard/pages/Dashboard'))
const CourseDetailPage = lazy(() => import('./features/courses/pages/CourseDetail'))
const StudentDashboardPage = lazy(() => import('./features/dashboard/pages/StudentDashboard'))
const StudentCourseDetailPage = lazy(() => import('./features/courses/pages/StudentCourseDetail'))
const InstructorDashboardPage = lazy(() => import('./features/dashboard/pages/InstructorDashboard'))
const HeadDashboardPage = lazy(() => import('./features/dashboard/pages/HeadDashboard'))
const StudentCoursesPage = lazy(() => import('./features/courses/pages/StudentCourses'))
const InstructorCoursesPage = lazy(() => import('./features/courses/pages/InstructorCourses'))
const HeadCoursesPage = lazy(() => import('./features/courses/pages/HeadCourses'))
const SettingsPage = lazy(() => import('./features/settings/pages/Settings'))
const SafetyPage = lazy(() => import('./features/settings/pages/Safety'))

// Loading fallback component for route transitions
function RouteLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading...</p>
      </div>
    </div>
  )
}

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
      <Route path="/student/courses/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<StudentCourseDetailPage />} />
      </Route>

      {/* Instructor routes - consistent nested structure */}
      <Route path="/instructor" element={<Layout showOnlyCoreItems={true} />}>
        <Route index element={<InstructorDashboardPage />} />
        <Route path="courses" element={<InstructorCoursesPage />} />
      </Route>
      <Route path="/instructor/course/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<CourseDetailPage />} />
      </Route>

      {/* Head routes - consistent nested structure */}
      <Route path="/head" element={<Layout showOnlyCoreItems={true} />}>
        <Route index element={<HeadDashboardPage />} />
        <Route path="courses" element={<HeadCoursesPage />} />
      </Route>
      <Route path="/head/course/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<CourseDetailPage />} />
      </Route>

      {/* Legacy routes - redirect to role-specific routes */}
      <Route path="/settings" element={<Layout />}>
        <Route index element={<SettingsPage />} />
      </Route>
      <Route path="/security" element={<Layout />}>
        <Route index element={<SafetyPage />} />
      </Route>
      <Route path="/lecturer" element={<Navigate to="/instructor" replace />} />
      <Route path="/course/:id" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}

export default App
