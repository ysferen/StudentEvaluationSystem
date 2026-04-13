import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CheckBadgeIcon,
  UserGroupIcon,
  ClipboardDocumentListIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

const features = [
  {
    icon: ChartBarIcon,
    title: 'Outcome Tracking',
    description: 'Map assessments to learning outcomes and program outcomes automatically.',
    accent: 'primary',
  },
  {
    icon: ArrowTrendingUpIcon,
    title: 'Data-Driven Insights',
    description: 'Visual dashboards that reveal trends across courses, departments, and programs.',
    accent: 'amber',
  },
  {
    icon: CheckBadgeIcon,
    title: 'Accreditation Ready',
    description: 'Generate reports that align with ABET and institutional accreditation standards.',
    accent: 'blue',
  },
  {
    icon: UserGroupIcon,
    title: 'Multi-Role Access',
    description: 'Tailored views for students, instructors, and department heads — one system, three perspectives.',
    accent: 'pink',
  },
  {
    icon: ClipboardDocumentListIcon,
    title: 'Assessment Management',
    description: 'Create, assign, and evaluate assessments with direct outcome alignment built in.',
    accent: 'violet',
  },
  {
    icon: ArrowPathIcon,
    title: 'Continuous Improvement',
    description: 'Close the loop — use evaluation data to refine curriculum and teaching methods cycle over cycle.',
    accent: 'green',
  },
]

const accentStyles: Record<string, { bg: string; icon: string }> = {
  primary: { bg: 'bg-primary-100', icon: 'text-primary-600' },
  amber: { bg: 'bg-amber-100', icon: 'text-amber-600' },
  blue: { bg: 'bg-blue-100', icon: 'text-blue-600' },
  pink: { bg: 'bg-pink-100', icon: 'text-pink-600' },
  violet: { bg: 'bg-violet-100', icon: 'text-violet-600' },
  green: { bg: 'bg-green-100', icon: 'text-green-600' },
}

const FeaturesSection = () => {
  return (
    <section id="features" className="py-20 sm:py-28 bg-secondary-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
            Everything you need to improve outcomes
          </h2>
          <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
            From assessment design to accreditation reports — one platform for the full cycle.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {features.map(({ icon: Icon, title, description, accent }) => (
            <div
              key={title}
              className="bg-white rounded-xl border border-secondary-200 p-6 sm:p-8 hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
            >
              <div
                className={`h-12 w-12 rounded-xl ${accentStyles[accent].bg} flex items-center justify-center mb-5`}
              >
                <Icon className={`h-6 w-6 ${accentStyles[accent].icon}`} />
              </div>
              <h3 className="text-lg font-bold text-secondary-900 mb-2">{title}</h3>
              <p className="text-secondary-500 text-sm leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
