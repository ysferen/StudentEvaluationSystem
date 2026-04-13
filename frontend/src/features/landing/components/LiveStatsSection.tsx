import { useLandingStats } from '../hooks/useLandingStats'

const stats = [
  { label: 'Universities', color: 'text-primary-600' },
  { label: 'Departments', color: 'text-violet-600' },
  { label: 'Programs', color: 'text-green-600' },
  { label: 'Courses', color: 'text-secondary-900' },
]

const LiveStatsSection = () => {
  const { data, isLoading } = useLandingStats()

  if (isLoading) {
    return (
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center gap-8 sm:gap-16">
            {stats.map(({ label }) => (
              <div key={label} className="text-center">
                <div className="h-10 w-16 bg-secondary-200 rounded animate-pulse mx-auto mb-2" />
                <div className="h-4 w-20 bg-secondary-100 rounded animate-pulse mx-auto" />
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (!data) return null

  const values = [data.universities, data.departments, data.programs, data.courses]

  return (
    <section className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-center gap-8 sm:gap-16">
          {stats.map(({ label, color }, i) => (
            <div key={label} className="text-center">
              <div className={`text-3xl sm:text-4xl font-bold ${color}`}>
                {values[i] >= 100 ? `${values[i]}+` : values[i]}
              </div>
              <div className="text-sm text-secondary-500 font-medium mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default LiveStatsSection
