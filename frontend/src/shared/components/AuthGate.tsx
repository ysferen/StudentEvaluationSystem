import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'

interface AuthGateProps {
  children: React.ReactNode
}

export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { isLoading, isAuthenticated, user } = useAuth()
  const location = useLocation()

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

  return <>{children}</>
}
