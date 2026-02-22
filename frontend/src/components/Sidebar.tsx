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
    ShieldCheckIcon,
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

    // Add a global Settings nav item for authenticated users,
    // but when inside settings/security show the focused account/security sidebar
    const inAccountArea = location.pathname.startsWith('/settings') || location.pathname.startsWith('/security')
    if (inAccountArea) {
        navigation = [
            { name: 'Account', href: '/settings', icon: Cog6ToothIcon },
            { name: 'Security', href: '/security', icon: ShieldCheckIcon },
        ]
    } else if (user && !showOnlyCoreItems) {
        const hasSettings = navigation.some(n => n.href === '/settings' || n.name === 'Settings')
        if (!hasSettings) {
            navigation.push({ name: 'Settings', href: '/settings', icon: Cog6ToothIcon })
        }
    }


    return (
        <>
            {/* Mobile sidebar backdrop */}
            {isOpen && (
                <div
                   className="fixed inset-0 bg-secondary-900/50 backdrop-blur-sm z-20 lg:hidden"
                    onClick={() => setIsOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={clsx(
                "fixed inset-y-0 left-0 z-10 w-64 h-screen bg-white/80 backdrop-blur-md border-r border-secondary-200 transform transition-transform duration-300 ease-in-out lg:h-auto lg:min-h-full lg:translate-x-0 lg:static lg:inset-auto",
                isOpen ? 'translate-x-0' : '-translate-x-full'
            )}>
                <div className="min-h-full flex flex-col">

                    {/* Navigation */}
                    <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto min-h-0">
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

                    {/* Bottom actions removed per UI change */}
                </div>
            </aside>
        </>
    )
}
