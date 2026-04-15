import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
]

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white shadow-sm'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span
              className={`font-bold text-lg transition-colors duration-300 ${
                scrolled ? 'text-secondary-900' : 'text-white'
              }`}
            >
              SES
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors duration-300 hover:text-primary-600 ${
                  scrolled ? 'text-secondary-600' : 'text-white/80'
                }`}
              >
                {link.label}
              </a>
            ))}
            <Link
              to="/login"
              className="px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-lg hover:bg-primary-700 transition-colors"
            >
              Sign In
            </Link>
          </div>

          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            <div className="space-y-1.5">
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
              <span
                className={`block w-6 h-0.5 transition-colors duration-300 ${
                  scrolled ? 'bg-secondary-900' : 'bg-white'
                }`}
              />
            </div>
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-secondary-200 shadow-lg">
          <div className="px-4 py-4 space-y-3">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="block text-secondary-700 hover:text-primary-600 font-medium text-sm"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <Link
              to="/login"
              className="block text-center px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-lg hover:bg-primary-700 transition-colors"
              onClick={() => setMobileOpen(false)}
            >
              Sign In
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

export default Navbar
