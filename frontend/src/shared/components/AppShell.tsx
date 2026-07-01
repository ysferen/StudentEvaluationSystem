import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { axiosInstance } from '@/shared/api/mutator'

interface AppShellProps {
  children?: React.ReactNode
  showOnlyCoreItems?: boolean
}

export const AppShell: React.FC<AppShellProps> = ({ children, showOnlyCoreItems = false }) => {
  const { user } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div
      className="min-h-screen bg-secondary-50"
      style={{ '--sidebar-width': '16rem' } as React.CSSProperties}
    >
      <div className="flex min-h-screen flex-col min-w-0 transition-all duration-300">
        <Header setSidebarOpen={setSidebarOpen} />

        {user?.impersonated_by && (
          <div className="fixed top-16 left-0 right-0 z-20 bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">
            Viewing as {user.first_name || user.username}.{' '}
            <button className="font-semibold underline" onClick={async () => {
              await axiosInstance.post('/api/users/users/return_from_impersonation/')
              window.location.href = '/head'
            }}>Return to Head account</button>
          </div>
        )}
        <div className={`flex flex-1 overflow-hidden ${user?.impersonated_by ? 'pt-24' : 'pt-16'}`}>
          <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} showOnlyCoreItems={showOnlyCoreItems} />

          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 lg:ml-[var(--sidebar-width)]">
            <div className="max-w-7xl mx-auto">
              {children || <Outlet />}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
