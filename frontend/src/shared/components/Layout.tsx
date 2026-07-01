import React from 'react'
import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { AppShell } from './AppShell'

interface LayoutProps {
  showOnlyCoreItems?: boolean
  requireAuth?: boolean
  children?: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ showOnlyCoreItems = false, requireAuth = true, children }) => {
  const { isLoading, isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (requireAuth) {
    if (isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-secondary-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
            <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
          </div>
        </div>
      )
    }

    if (!isAuthenticated) {
      return <Navigate to="/login" replace />
    }

    if (user?.must_change_password && location.pathname !== '/security') {
      return <Navigate to="/security" replace />
    }
  }

  return <AppShell showOnlyCoreItems={showOnlyCoreItems}>{children || <Outlet />}</AppShell>
}

export default Layout
