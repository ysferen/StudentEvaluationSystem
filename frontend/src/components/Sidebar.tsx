import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
    HomeIcon,
    DocumentTextIcon,
    ChartBarIcon,
    UsersIcon,
    Cog6ToothIcon,
    ArrowRightStartOnRectangleIcon,
    ClipboardDocumentListIcon,
    ChartPieIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

interface SidebarProps {
    isOpen: boolean
    setIsOpen: (isOpen: boolean) => void
    showOnlyCoreItems?: boolean
}

interface NavItem {
    name: string
    href: string
    icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
    roles?: string[]
}

const getNavigationForRole = (role: string | null): NavItem[] => {
    if (!role) {
        return [
            { name: 'Dashboard', href: '/', icon: HomeIcon },
        ]
    }

    const baseNavigation: NavItem[] = []

    if (role === 'student') {
        return [
            ...baseNavigation,
            { name: 'Analytics', href: `/${role}/analytics`, icon: ChartBarIcon, roles: ['student'] },
            { name: 'Assignments', href: `/${role}/assignments`, icon: ClipboardDocumentListIcon, roles: ['student'] },
            { name: 'Outcomes', href: `/${role}/outcomes`, icon: ChartPieIcon, roles: ['student'] },
        ]
    }

    if (role === 'instructor') {
        return [
            ...baseNavigation,
            { name: 'Assessments', href: `/${role}/assessments`, icon: DocumentTextIcon, roles: ['instructor'] },
            { name: 'Outcomes', href: `/${role}/outcomes`, icon: ChartBarIcon, roles: ['instructor'] },
            { name: 'Students', href: `/${role}/students`, icon: UsersIcon, roles: ['instructor'] },
            { name: 'Analytics', href: `/${role}/analytics`, icon: ChartBarIcon, roles: ['instructor'] },
        ]
    }

    if (role === 'admin' || role === 'head') {
        return [
            ...baseNavigation,
            { name: 'Assessments', href: `/${role}/assessments`, icon: DocumentTextIcon, roles: ['admin', 'head'] },
            { name: 'Outcomes', href: `/${role}/outcomes`, icon: ChartBarIcon, roles: ['admin', 'head'] },
            { name: 'Students', href: `/${role}/students`, icon: UsersIcon, roles: ['admin', 'head'] },
            { name: 'Analytics', href: `/${role}/analytics`, icon: ChartBarIcon, roles: ['admin', 'head'] },
        ]
    }

    return baseNavigation
}

export const Sidebar = ({ isOpen, setIsOpen, showOnlyCoreItems = false }: SidebarProps) => {
    const { user, logout } = useAuth()
    const location = useLocation()
    const navigate = useNavigate()

    let navigation: NavItem[] = []
    navigation = showOnlyCoreItems ? [] : getNavigationForRole(user?.role || null)


    return (
        <>
            {/* Mobile sidebar backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-secondary-900/50 backdrop-blur-sm z-40 lg:hidden"
                    onClick={() => setIsOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={clsx(
                "fixed inset-y-0 left-0 z-50 w-64 bg-white/80 backdrop-blur-md border-r border-secondary-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-auto",
                isOpen ? 'translate-x-0' : '-translate-x-full'
            )}>
                <div className="h-full flex flex-col">

                    {/* Navigation */}
                    <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
                        {navigation.map((item: NavItem) => {
                            // Check if this is a hash link (for student course detail)
                            const isHashLink = item.href.startsWith('#')
                            // For hash links, check against window.location.hash
                            const isActive = isHashLink
                                ? window.location.hash === item.href
                                : location.pathname === item.href

                            if (isHashLink) {
                                return (
                                    <a
                                        key={item.name}
                                        href={item.href}
                                        className={clsx(
                                            "flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 group",
                                            isActive
                                                ? 'bg-primary-50 text-primary-700 shadow-sm'
                                                : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                                        )}
                                    >
                                        <item.icon className={clsx(
                                            "h-6 w-6 transition-colors duration-200",
                                            isActive ? 'text-primary-600' : 'text-secondary-400 group-hover:text-secondary-600'
                                        )} />
                                        <span>{item.name}</span>
                                    </a>
                                )
                            }

                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={clsx(
                                        "flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 group",
                                        isActive
                                            ? 'bg-primary-50 text-primary-700 shadow-sm'
                                            : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                                    )}
                                >
                                    <item.icon className={clsx(
                                        "h-6 w-6 transition-colors duration-200",
                                        isActive ? 'text-primary-600' : 'text-secondary-400 group-hover:text-secondary-600'
                                    )} />
                                    <span>{item.name}</span>
                                </Link>
                            )
                        })}
                    </nav>

                    {/* Bottom actions */}
                    <div className="p-4 border-t border-secondary-200/50 space-y-1">
                        {user ? (
                            <>
                                <Link
                                    to="/settings"
                                    className="flex items-center space-x-3 px-4 py-3 rounded-xl font-medium text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900 transition-colors group"
                                >
                                    <Cog6ToothIcon className="h-6 w-6 text-secondary-400 group-hover:text-secondary-600 transition-colors" />
                                    <span>Settings</span>
                                </Link>
                                <button
                                    className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-medium text-danger-600 hover:bg-danger-50 transition-colors group"
                                    onClick={() => {
                                        logout()
                                        navigate('/login')
                                    }}
                                >
                                    <ArrowRightStartOnRectangleIcon className="h-6 w-6 group-hover:text-danger-700 transition-colors" />
                                    <span>Sign Out</span>
                                </button>
                            </>
                        ) : (
                            <Link
                                to="/login"
                                className="flex items-center space-x-3 px-4 py-3 rounded-xl font-medium text-primary-600 hover:bg-primary-50 transition-colors group"
                            >
                                <ArrowRightStartOnRectangleIcon className="h-6 w-6 group-hover:text-primary-700 transition-colors" />
                                <span>Sign In</span>
                            </Link>
                        )}
                    </div>
                </div>
            </aside>
        </>
    )
}
