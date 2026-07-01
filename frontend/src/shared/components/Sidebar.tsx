import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../features/auth/hooks/useAuth'
import { Home, FileText, BarChart3, Users, Settings, ClipboardList, PieChart, ShieldCheck, Building2 } from 'lucide-react'
import clsx from 'clsx'

type Role = 'student' | 'instructor' | 'program_head' | 'admin' | 'guest'

interface SidebarProps {
    isOpen: boolean
    setIsOpen: (isOpen: boolean) => void
    showOnlyCoreItems?: boolean
}

interface NavItem {
    name: string
    href: string
    icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}

interface RoleNavigation {
    default: NavItem[]
    courseDetail?: NavItem[]
}

const courseDetailNavigation: NavItem[] = [
    { name: 'Outcomes', href: '#outcomes', icon: BarChart3 },
    { name: 'Assessments', href: '#assessments', icon: FileText },
    { name: 'Students', href: '#students', icon: Users },
    { name: 'Settings', href: '/settings', icon: Settings },
]

const studentCourseDetailNavigation: NavItem[] = [
    { name: 'Assessments', href: '#assessments', icon: FileText },
    { name: 'Outcomes', href: '#outcomes', icon: BarChart3 },
    { name: 'Analytics', href: '#analytics', icon: PieChart },
]

const programPageNavigation: NavItem[] = [
    { name: 'Overview', href: '#overview', icon: Building2 },
    { name: 'Outcomes', href: '#outcomes', icon: BarChart3 },
    { name: 'Year Levels', href: '#year-levels', icon: Users },
    { name: 'Analytics', href: '#analytics', icon: PieChart },
    { name: 'Settings', href: '/settings', icon: Settings },
]

const roleConfig: Record<Role, RoleNavigation> = {
    student: {
        default: [
            { name: 'Dashboard', href: '/student', icon: Home },
            { name: 'Courses', href: '/student/courses', icon: ClipboardList },
        ],
    },
    instructor: {
        default: [
            { name: 'Dashboard', href: '/instructor', icon: Home },
            { name: 'Courses', href: '/instructor/courses', icon: ClipboardList },
        ],
        courseDetail: courseDetailNavigation,
    },
    program_head: {
        default: [
            { name: 'Dashboard', href: '/head', icon: Home },
            { name: 'Program', href: '/head/program', icon: Building2 },
            { name: 'Courses', href: '/head/courses', icon: ClipboardList },
            { name: 'Permissions', href: '/head/permissions', icon: ShieldCheck },
            { name: 'People', href: '/head/people', icon: Users },
        ],
        courseDetail: courseDetailNavigation,
    },
    admin: {
        default: [
            { name: 'System Setup', href: '/system-admin', icon: Home },
        ],
        courseDetail: courseDetailNavigation,
    },
    guest: {
        default: [],
    },
}

const getNavigationForRole = (role: string | null): NavItem[] => {
    if (!role) return [{ name: 'Dashboard', href: '/', icon: Home }]
    const config = roleConfig[role as Role]
    if (!config) return []
    return config.default
}

export const Sidebar = ({ isOpen, setIsOpen, showOnlyCoreItems = false }: SidebarProps) => {
    const { user } = useAuth()
    const location = useLocation()
    const isStaffCourseDetailPage = /^\/(instructor|head)\/course\/[^/]+\/?$/.test(location.pathname)
    const isStudentCourseDetailPage = /^\/student\/courses\/[^/]+\/?$/.test(location.pathname)
    const isProgramPage = /^\/head\/program\/?$/.test(location.pathname)
    const isPageLocalNavigation = isStaffCourseDetailPage || isStudentCourseDetailPage || isProgramPage

    let navigation: NavItem[] = []
    if (isStaffCourseDetailPage) {
        navigation = courseDetailNavigation
    } else if (isStudentCourseDetailPage) {
        navigation = studentCourseDetailNavigation
    } else if (isProgramPage) {
        navigation = programPageNavigation
    } else {
        navigation = getNavigationForRole(user?.role || null)
    }

    const inAccountArea = location.pathname.startsWith('/settings') || location.pathname.startsWith('/security')
    if (inAccountArea) {
        navigation = [
            { name: 'Account', href: '/settings', icon: Settings },
            { name: 'Security', href: '/security', icon: ShieldCheck },
        ]
    } else if (user && !isPageLocalNavigation) {
        const hasSettings = navigation.some(n => n.href === '/settings' || n.name === 'Settings')
        if (!hasSettings) {
            navigation.push({ name: 'Settings', href: '/settings', icon: Settings })
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
                "fixed inset-y-0 left-0 z-30 w-[var(--sidebar-width)] bg-white/80 backdrop-blur-md border-r border-secondary-200 transform transition-transform duration-300 ease-in-out lg:top-16 lg:bottom-0 lg:translate-x-0",
                isOpen ? 'translate-x-0' : '-translate-x-full'
            )} data-core-only={showOnlyCoreItems || undefined}>
                <div className="min-h-full flex flex-col">

                    {/* Navigation */}
                    <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto min-h-0">
                        {navigation.map((item: NavItem) => {
                            const isHashLink = item.href.startsWith('#')
                            const isActive = isHashLink
                                ? location.hash === item.href
                                : location.pathname === item.href

                            if (isHashLink) {
                                return (
                                    <button
                                        key={item.name}
                                        type="button"
                                        onClick={() => {
                                            const target = document.getElementById(item.href.slice(1))
                                            target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                            window.history.replaceState(null, '', item.href)
                                        }}
                                        className={clsx(
                                            "w-full flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 group text-left",
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
                                    </button>
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
