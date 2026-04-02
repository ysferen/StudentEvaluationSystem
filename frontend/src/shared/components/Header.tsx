import {
    Bars3Icon,
    UserCircleIcon,
    EllipsisVerticalIcon,
    Cog6ToothIcon,
    ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { NavLink, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../features/auth/hooks/useAuth'
import { useState, useRef, useEffect } from 'react'

interface HeaderProps {
    setSidebarOpen: (isOpen: boolean) => void
}

export const Header = ({ setSidebarOpen }: HeaderProps) => {
    const { user, logout } = useAuth()
    const [menuOpen, setMenuOpen] = useState(false)
    const menuRef = useRef<HTMLDivElement | null>(null)
    const navigate = useNavigate()

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const getNavItems = () => {
        switch (user?.role) {
            case 'student':
                return [
                    { to: '/student', label: 'Homepage' },
                    { to: '/student/courses', label: 'Courses' }
                ]
            case 'instructor':
                return [
                    { to: '/instructor', label: 'Homepage' },
                    { to: '/instructor/courses', label: 'Courses' }
                ]
            case 'admin':
                return [
                    { to: '/head', label: 'Homepage' },
                    { to: '/head/courses', label: 'Courses' }
                ]
            default:
                return []
        }
    }

    const navItems = getNavItems()

    return (
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-secondary-200 sticky top-0 z-30">
            <div className="h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between relative">
                {/* Mobile menu button */}
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="lg:hidden p-2 rounded-full hover:bg-secondary-100 transition-colors"
                    aria-label="Open menu"
                >
                    <Bars3Icon className="h-6 w-6 text-secondary-600" />
                </button>

                {/* Logo (left) and Navigation buttons */}
                <div className="flex items-center">
                    <Link to="/" className="hidden sm:flex items-center mr-4">
                        <span className="text-xl font-bold text-secondary-900 tracking-tight">SES</span>
                    </Link>
                    {/* Divider between logo and navigation */}
                        <div className="hidden sm:block h-12 self-center border-l border-secondary-200 mr-4" aria-hidden="true" />
                    <div className="flex-1 flex items-center space-x-6">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.label === 'Homepage'}
                            className={({ isActive }) =>
                                `font-medium transition-colors ${
                                    isActive
                                        ? 'text-primary-600'
                                        : 'text-secondary-600 hover:text-primary-600'
                                }`
                            }
                        >
                            {item.label}
                        </NavLink>
                    ))}
                    </div>
                </div>
                <div className="flex items-center space-x-4">
                    {user ? (
                        <>
                            {/* Bell icon commented out */}
                            {/* <button className="p-2 rounded-full hover:bg-secondary-100 transition-colors relative group">
                                <BellIcon className="h-6 w-6 text-secondary-600 group-hover:text-secondary-900 transition-colors" />
                                <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 bg-danger-500 border-2 border-white rounded-full"></span>
                            </button> */}
                            <div className="flex items-center space-x-3 pl-4 border-l border-secondary-200">
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-semibold text-secondary-900">
                                        {user.first_name || user.username} {user.last_name || ''}
                                    </p>
                                    <p className="text-xs text-secondary-500 capitalize">{user.role}</p>
                                </div>
                                <div className="inline-flex items-center" ref={menuRef}>
                                    <div className="p-1 rounded-full">
                                        <UserCircleIcon className="h-9 w-9 text-secondary-400" />
                                    </div>
                                    <button
                                        aria-expanded={menuOpen}
                                        onClick={() => setMenuOpen((s) => !s)}
                                        className="ml-1 p-2 rounded-full hover:bg-secondary-100 transition-colors inline-flex items-center"
                                    >
                                        <EllipsisVerticalIcon className="h-6 w-6 text-secondary-600" />
                                    </button>
                                    {menuOpen && (
                                        <div className="absolute right-4 top-full mt-2 w-40 bg-white border border-secondary-200 rounded-md shadow-lg py-1 z-50">
                                            <button
                                                onClick={() => {
                                                    setMenuOpen(false)
                                                    navigate('/settings')
                                                }}
                                                className="w-full text-left px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-100 flex items-center"
                                            >
                                                <Cog6ToothIcon className="h-4 w-4 mr-2 text-secondary-500" />
                                                Settings
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setMenuOpen(false)
                                                    logout()
                                                }}
                                                className="w-full text-left px-4 py-2 text-sm text-danger-600 hover:bg-danger-50 flex items-center"
                                            >
                                                <ArrowRightOnRectangleIcon className="h-4 w-4 mr-2 text-danger-600" />
                                                Sign out
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex items-center space-x-3">
                            <span className="text-sm text-secondary-500 font-medium">Guest Mode</span>
                            <Link
                                to="/login"
                                className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
                            >
                                Sign In
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}
