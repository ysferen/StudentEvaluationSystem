import {
  AcademicCapIcon,
  UserGroupIcon,
  BuildingLibraryIcon,
} from '@heroicons/react/24/outline'

const roles = [
  {
    icon: AcademicCapIcon,
    title: 'Students',
    description:
      'Track your progress across courses. See how each assessment contributes to your learning outcomes and where you stand.',
    features: ['Course outcome breakdown', 'Personal achievement tracking', 'Visual progress dashboards'],
    accent: 'primary',
    cta: 'Explore student view',
    href: '/login',
  },
  {
    icon: UserGroupIcon,
    title: 'Instructors',
    description:
      "Manage assessments and see how students perform against learning outcomes. Identify what's working and what's not.",
    features: ['Assessment creation & LO mapping', 'Class outcome analytics', 'Student performance comparison'],
    accent: 'violet',
    cta: 'Explore instructor view',
    href: '/login',
  },
  {
    icon: BuildingLibraryIcon,
    title: 'Department Heads',
    description:
      'Oversee program-level outcomes and generate accreditation reports. Make strategic decisions backed by real data.',
    features: ['Program outcome dashboards', 'Cross-course LO analysis', 'Accreditation report generation'],
    accent: 'green',
    cta: 'Explore head view',
    href: '/login',
  },
]

const accentMap: Record<string, { icon: string; bg: string; check: string; link: string; border: string }> = {
  primary: { icon: 'bg-primary-600', bg: 'bg-primary-100', check: 'text-primary-600', link: 'text-primary-500', border: 'border-primary-600/20' },
  violet: { icon: 'bg-violet-600', bg: 'bg-violet-100', check: 'text-violet-600', link: 'text-violet-500', border: 'border-violet-600/20' },
  green: { icon: 'bg-green-600', bg: 'bg-green-100', check: 'text-green-600', link: 'text-green-500', border: 'border-green-600/20' },
}

const RoleCardsSection = () => {
  return (
    <section id="roles" className="py-20 sm:py-28 bg-secondary-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            One platform, three perspectives
          </h2>
          <p className="text-lg text-secondary-400 max-w-2xl mx-auto">
            Each role gets a tailored experience
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {roles.map(({ icon: Icon, title, description, features, accent, cta, href }) => {
            const styles = accentMap[accent]
            return (
              <div
                key={title}
                className={`bg-secondary-800 rounded-xl p-6 sm:p-8 border ${styles.border} hover:border-opacity-60 transition-all duration-300`}
              >
                <div className={`w-12 h-12 rounded-xl ${styles.icon} flex items-center justify-center mb-4`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
                <p className="text-secondary-400 text-sm leading-relaxed mb-5">{description}</p>
                <ul className="space-y-2 mb-6">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-secondary-300 text-sm">
                      <span className={styles.check}>✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>
                <a
                  href={href}
                  className={`${styles.link} text-sm font-semibold hover:underline`}
                >
                  {cta} →
                </a>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default RoleCardsSection
