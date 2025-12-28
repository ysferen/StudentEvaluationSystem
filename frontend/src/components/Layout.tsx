import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  showOnlyCoreItems?: boolean
  children?: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ showOnlyCoreItems = false, children }) => {
  const { isLoading } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-secondary-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  // Removed authentication check to allow guest access

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

export default Layout
