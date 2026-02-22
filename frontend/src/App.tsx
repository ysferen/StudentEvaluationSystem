import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'

// Lazy load all page components for code splitting
const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CourseDetail = lazy(() => import('./pages/CourseDetail'))
const StudentDashboard = lazy(() => import('./pages/StudentDashboard'))
const StudentCourseDetail = lazy(() => import('./pages/StudentCourseDetail'))
const InstructorDashboard = lazy(() => import('./pages/InstructorDashboard'))
const HeadDashboard = lazy(() => import('./pages/HeadDashboard'))
const StudentCourses = lazy(() => import('./pages/StudentCourses'))
const InstructorCourses = lazy(() => import('./pages/InstructorCourses'))
const HeadCourses = lazy(() => import('./pages/HeadCourses'))
const Settings = lazy(() => import('./pages/Settings'))
const Safety = lazy(() => import('./pages/Safety'))

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
        <Route path="/login" element={<Login />} />

      {/* Student routes with shared layout */}
      <Route path="/student" element={<Layout showOnlyCoreItems={true} />}>
        <Route index element={<StudentDashboard />} />
        <Route path="courses" element={<StudentCourses />} />
      </Route>
      <Route path="/student/courses/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<StudentCourseDetail />} />
      </Route>

      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
      </Route>

      {/* Instructor routes - consistent nested structure */}
      <Route path="/instructor" element={<Layout showOnlyCoreItems={true} />}>
        <Route index element={<InstructorDashboard />} />
        <Route path="courses" element={<InstructorCourses />} />
      </Route>
      <Route path="/instructor/course/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<CourseDetail />} />
      </Route>

      {/* Head routes - consistent nested structure */}
      <Route path="/head" element={<Layout showOnlyCoreItems={true} />}>
        <Route index element={<HeadDashboard />} />
        <Route path="courses" element={<HeadCourses />} />
      </Route>
      <Route path="/head/course/:id" element={<Layout showOnlyCoreItems={false} />}>
        <Route index element={<CourseDetail />} />
      </Route>

      {/* Legacy routes - redirect to role-specific routes */}
      <Route path="/settings" element={<Layout />}>
        <Route index element={<Settings />} />
      </Route>
      <Route path="/security" element={<Layout />}>
        <Route index element={<Safety />} />
      </Route>
      <Route path="/lecturer" element={<Navigate to="/instructor" replace />} />
      <Route path="/course/:id" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}

export default App
