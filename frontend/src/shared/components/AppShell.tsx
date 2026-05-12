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

  return (
    <div className="min-h-screen bg-secondary-50">
      <div className="flex-1 flex flex-col min-w-0 transition-all duration-300">
        <Header setSidebarOpen={setSidebarOpen} />

        <div className="flex-1 flex overflow-hidden">
          {!showOnlyCoreItems && (
            <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} showOnlyCoreItems={showOnlyCoreItems} />
          )}

          <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
            <div className="max-w-7xl mx-auto">
              {children || <Outlet />}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
