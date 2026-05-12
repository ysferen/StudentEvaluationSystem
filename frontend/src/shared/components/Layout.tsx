import React from 'react'
import { Outlet } from 'react-router-dom'
import { AuthGate } from './AuthGate'
import { AppShell } from './AppShell'

interface LayoutProps {
  showOnlyCoreItems?: boolean
  requireAuth?: boolean
  children?: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ showOnlyCoreItems = false, requireAuth = true, children }) => {
  if (requireAuth) {
    return (
      <AuthGate>
        <AppShell showOnlyCoreItems={showOnlyCoreItems}>{children || <Outlet />}</AppShell>
      </AuthGate>
    )
  }

  return <AppShell showOnlyCoreItems={showOnlyCoreItems}>{children || <Outlet />}</AppShell>
}

export default Layout
