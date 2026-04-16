const GuestDashboard = () => {
  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-teal-600 to-cyan-600 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Welcome to SES</h1>
          <p className="text-teal-100 text-lg">Student Evaluation System</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-secondary-200 p-6">
        <h2 className="text-xl font-semibold text-secondary-900 mb-4">Guest Access</h2>
        <p className="text-secondary-600">
          Please log in to access the full dashboard and evaluation features.
        </p>
      </div>
    </div>
  )
}

export default GuestDashboard
