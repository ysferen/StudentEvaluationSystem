import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { GraduationCap, BookOpen, ChartNoAxesCombined, Target } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import { Card } from '@/components/ui/custom/Card'
import { LazyChartWidget as ChartWidget } from '@/components/ui/custom/LazyChartWidget'
import { evaluationGradesCourseAveragesRetrieve } from '../../../shared/api/generated/evaluation/evaluation'
import { fetchAllEvaluationEnrollments } from '@/shared/api/enrollments'
import { coreStudentPoScoresList } from '../../../shared/api/generated/scores/scores'
import type { CourseEnrollment, StudentProgramOutcomeScore } from '../../../shared/api/model'

const StudentDashboard = () => {
  const { user } = useAuth()
  const userId = user?.id
  const results = useQueries({ queries: [
    { queryKey: ['student-enrollments', userId], queryFn: () => userId ? fetchAllEvaluationEnrollments({ student: userId }) : Promise.reject(new Error('Student is required')), enabled: Boolean(userId) },
    { queryKey: ['student-po-scores', userId], queryFn: () => coreStudentPoScoresList({ student: userId }), enabled: Boolean(userId) },
    { queryKey: ['student-course-averages', userId], queryFn: () => userId ? evaluationGradesCourseAveragesRetrieve({ student: userId }) : Promise.reject(new Error('Student is required')), enabled: Boolean(userId) },
  ] })
  const [enrollmentsQuery, poScoresQuery, courseAveragesQuery] = results
  const enrollments = useMemo(() => (enrollmentsQuery.data?.results ?? []) as CourseEnrollment[], [enrollmentsQuery.data])
  const poScores = useMemo(() => (poScoresQuery.data?.results ?? []) as StudentProgramOutcomeScore[], [poScoresQuery.data])
  const courseScores = useMemo(() => (courseAveragesQuery.data ?? []) as Array<{ course_id: number; weighted_average: number | null }>, [courseAveragesQuery.data])
  const scoresByCourse = useMemo(() => new Map(courseScores.map(score => [score.course_id, score.weighted_average])), [courseScores])
  const scoredCourses = courseScores.filter(score => score.weighted_average !== null)
  const average = scoredCourses.length ? scoredCourses.reduce((sum, score) => sum + (score.weighted_average ?? 0), 0) / scoredCourses.length : null
  const credits = enrollments.reduce((sum, enrollment) => sum + (enrollment.course.credits ?? 0), 0)
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Student'

  if (results.some(query => query.isLoading)) return <div className="flex min-h-96 items-center justify-center"><div className="text-center"><div className="mx-auto h-14 w-14 animate-spin rounded-full border-b-4 border-primary-600" /><p className="mt-4 text-secondary-600">Loading your progress…</p></div></div>
  if (results.some(query => query.isError)) return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-800">Your dashboard could not be loaded. <button className="ml-2 font-semibold" onClick={() => results.forEach(query => void query.refetch())}>Try again</button></div>

  const metrics = [
    { label: 'Current courses', value: enrollments.length, icon: BookOpen, color: 'bg-sky-100 text-sky-700' },
    { label: 'Average score', value: average === null ? '—' : average.toFixed(1), icon: ChartNoAxesCombined, color: 'bg-emerald-100 text-emerald-700' },
    { label: 'Current credits', value: credits, icon: GraduationCap, color: 'bg-violet-100 text-violet-700' },
    { label: 'Outcomes measured', value: poScores.length, icon: Target, color: 'bg-amber-100 text-amber-700' },
  ]
  const courseChart = enrollments.map(enrollment => ({ code: enrollment.course.code, score: scoresByCourse.get(enrollment.course.id) ?? 0 }))

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-cyan-950 to-teal-700 p-8 text-white shadow-xl"><div className="relative z-10"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-teal-200">Student overview</p><h1 className="mt-2 text-3xl font-bold">Welcome, {displayName}</h1><p className="mt-2 text-teal-100">A private view of your courses and learning-outcome progress.</p></div><div className="absolute -right-12 -top-20 h-72 w-72 rounded-full bg-white/10 blur-2xl" /></header>

    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(metric => <Card key={metric.label} variant="flat"><div className="flex items-center gap-4"><div className={`rounded-2xl p-3 ${metric.color}`}><metric.icon className="h-6 w-6" /></div><div><p className="text-sm text-secondary-500">{metric.label}</p><p className="text-2xl font-bold text-secondary-900">{metric.value}</p></div></div></Card>)}</section>

    <section className="grid gap-6 xl:grid-cols-2">
      <ChartWidget title="Course performance" subtitle="Your weighted average in each current course" type="bar" series={[{ name: 'Score', data: courseChart.map(item => item.score) }]} options={{ colors: ['#0891b2'], xaxis: { categories: courseChart.map(item => item.code) }, yaxis: { min: 0, max: 100 }, plotOptions: { bar: { borderRadius: 6, columnWidth: '48%' } }, dataLabels: { enabled: false } }} height={360} />
      <ChartWidget title="Program outcome progress" subtitle="Your achievement by program outcome" type="radar" series={[{ name: 'Achievement', data: poScores.map(score => Math.round(score.score ?? 0)) }]} options={{ colors: ['#0d9488'], xaxis: { categories: poScores.map(score => score.program_outcome.code) }, yaxis: { min: 0, max: 100, tickAmount: 5 }, stroke: { width: 2 }, fill: { opacity: 0.25 }, markers: { size: 4 } }} height={360} />
    </section>

    <section><div className="mb-4"><h2 className="text-xl font-bold text-secondary-900">Your courses</h2><p className="text-sm text-secondary-500">Only courses attached to your own enrollment are shown.</p></div>{enrollments.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{enrollments.map(enrollment => { const score = scoresByCourse.get(enrollment.course.id); return <Link key={enrollment.id} to={`/student/courses/${enrollment.course.id}`}><Card variant="hover" className="h-full"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-bold text-primary-700">{enrollment.course.code}</p><h3 className="mt-1 font-semibold text-secondary-900">{enrollment.course.name}</h3></div><span className="rounded-full bg-secondary-100 px-2.5 py-1 text-xs text-secondary-600">{enrollment.course.credits} CR</span></div><div className="mt-5"><div className="mb-2 flex justify-between text-sm"><span className="text-secondary-500">Weighted score</span><b>{score == null ? 'Not available' : score.toFixed(1)}</b></div><div className="h-2 overflow-hidden rounded-full bg-secondary-100"><div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-500" style={{ width: `${Math.max(0, Math.min(100, score ?? 0))}%` }} /></div></div></Card></Link> })}</div> : <Card className="py-12 text-center"><BookOpen className="mx-auto h-10 w-10 text-secondary-300" /><h3 className="mt-3 font-semibold">No current courses</h3><p className="text-sm text-secondary-500">Your enrolled courses will appear here.</p></Card>}</section>
  </div>
}

export default StudentDashboard
