import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

interface AppShellProps {
  children?: React.ReactNode
  showOnlyCoreItems?: boolean
}

export const AppShell: React.FC<AppShellProps> = ({ children, showOnlyCoreItems = false }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const hasSidebar = !showOnlyCoreItems

  return (
    <div
      className="min-h-screen bg-secondary-50"
      style={{ '--sidebar-width': '16rem' } as React.CSSProperties}
    >
      <div className="flex min-h-screen flex-col min-w-0 transition-all duration-300">
        <Header setSidebarOpen={setSidebarOpen} showOnlyCoreItems={showOnlyCoreItems} />

        <div className="flex flex-1 pt-16 overflow-hidden">
          {hasSidebar && (
            <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} showOnlyCoreItems={showOnlyCoreItems} />
          )}

          <main className={`flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 ${hasSidebar ? 'lg:ml-[var(--sidebar-width)]' : ''}`}>
            <div className="max-w-7xl mx-auto">
              {children || <Outlet />}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
