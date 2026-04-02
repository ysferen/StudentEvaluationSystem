import { Link } from 'react-router-dom'
import { Card } from '../../../shared/components/ui/Card'
import {
    AcademicCapIcon,
    BuildingLibraryIcon,
    BookOpenIcon,
    ArrowRightIcon
} from '@heroicons/react/24/outline'

const GuestDashboard = () => {
    return (
        <div className="space-y-8">
            {/* Hero Section */}
            <div className="relative overflow-hidden rounded-2xl bg-primary-600 p-8 sm:p-12 text-white shadow-lg">
                <div className="relative z-10 max-w-3xl">
                    <h1 className="text-3xl sm:text-4xl font-bold mb-4">Welcome to Student Evaluation System</h1>
                    <p className="text-teal-100 text-lg mb-8">
                        Explore our universities, departments, and programs. Sign in to access your personalized dashboard, view assessments, and track your progress.
                    </p>
                    <div className="flex flex-wrap gap-4">
                        <Link
                            to="/login"
                            className="px-6 py-3 bg-white text-primary-600 font-semibold rounded-xl shadow-lg hover:bg-primary-50 transition-colors"
                        >
                            Sign In
                        </Link>
                        <Link
                            to="/universities"
                            className="px-6 py-3 bg-primary-700 text-white font-semibold rounded-xl hover:bg-primary-800 transition-colors"
                        >
                            Explore Universities
                        </Link>
                    </div>
                </div>
                <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
                <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
            </div>

            {/* Quick Links Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Link to="/universities" className="group">
                    <Card variant="hover" className="h-full flex flex-col items-center text-center p-8 transition-all duration-300 group-hover:-translate-y-1">
                        <div className="h-16 w-16 rounded-2xl bg-primary-100 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                            <AcademicCapIcon className="h-8 w-8 text-primary-600" />
                        </div>
                        <h3 className="text-xl font-bold text-secondary-900 mb-2">Universities</h3>
                        <p className="text-secondary-500 mb-6">Browse all registered universities and their details.</p>
                        <div className="mt-auto flex items-center text-primary-600 font-medium group-hover:gap-2 transition-all">
                            <span>Browse</span>
                            <ArrowRightIcon className="h-4 w-4 ml-1" />
                        </div>
                    </Card>
                </Link>

                <Link to="/departments" className="group">
                    <Card variant="hover" className="h-full flex flex-col items-center text-center p-8 transition-all duration-300 group-hover:-translate-y-1">
                        <div className="h-16 w-16 rounded-2xl bg-cyan-100 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                            <BuildingLibraryIcon className="h-8 w-8 text-cyan-700" />
                        </div>
                        <h3 className="text-xl font-bold text-secondary-900 mb-2">Departments</h3>
                        <p className="text-secondary-500 mb-6">Explore various departments and their academic offerings.</p>
                        <div className="mt-auto flex items-center text-cyan-700 font-medium group-hover:gap-2 transition-all">
                            <span>Explore</span>
                            <ArrowRightIcon className="h-4 w-4 ml-1" />
                        </div>
                    </Card>
                </Link>

                <Link to="/programs" className="group">
                    <Card variant="hover" className="h-full flex flex-col items-center text-center p-8 transition-all duration-300 group-hover:-translate-y-1">
                        <div className="h-16 w-16 rounded-2xl bg-emerald-100 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                            <BookOpenIcon className="h-8 w-8 text-emerald-700" />
                        </div>
                        <h3 className="text-xl font-bold text-secondary-900 mb-2">Programs</h3>
                        <p className="text-secondary-500 mb-6">View available academic programs and course structures.</p>
                        <div className="mt-auto flex items-center text-emerald-700 font-medium group-hover:gap-2 transition-all">
                            <span>View</span>
                            <ArrowRightIcon className="h-4 w-4 ml-1" />
                        </div>
                    </Card>
                </Link>
            </div>

            {/* Info Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <Card className="p-8 bg-gradient-to-br from-secondary-900 to-secondary-800 text-white border-none">
                    <h3 className="text-2xl font-bold mb-4">About the System</h3>
                    <p className="text-secondary-300 leading-relaxed mb-6">
                        The Student Evaluation System is a comprehensive platform designed to streamline academic assessments,
                        track learning outcomes, and facilitate continuous improvement in education quality.
                    </p>
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <p className="text-3xl font-bold text-teal-400 mb-1">100+</p>
                            <p className="text-secondary-400 text-sm">Courses</p>
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-cyan-400 mb-1">50+</p>
                            <p className="text-secondary-400 text-sm">Programs</p>
                        </div>
                    </div>
                </Card>

                <Card className="p-8">
                    <h3 className="text-2xl font-bold text-secondary-900 mb-4">Latest Updates</h3>
                    <div className="space-y-4">
                        {[
                            { title: 'New Assessment Guidelines', date: 'Nov 24, 2025', type: 'Policy' },
                            { title: 'Fall Semester Registration', date: 'Nov 20, 2025', type: 'Academic' },
                            { title: 'System Maintenance', date: 'Nov 15, 2025', type: 'System' },
                        ].map((update, index) => (
                            <div key={index} className="flex items-start justify-between pb-4 border-b border-secondary-100 last:border-0 last:pb-0">
                                <div>
                                    <h4 className="font-semibold text-secondary-900">{update.title}</h4>
                                    <p className="text-sm text-secondary-500">{update.date}</p>
                                </div>
                                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary-100 text-secondary-600">
                                    {update.type}
                                </span>
                            </div>
                        ))}
                    </div>
                </Card>
            </div>
        </div>
    )
}

export default GuestDashboard
