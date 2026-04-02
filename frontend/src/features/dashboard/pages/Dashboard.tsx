import { useAuth } from '../../auth/hooks/useAuth'
import { Navigate } from 'react-router-dom'
import GuestDashboard from './GuestDashboard'

const Dashboard = () => {
  const { user } = useAuth()

  if (!user) {
    return <GuestDashboard />
  }

  const getRoleBasedDashboard = () => {
    switch (user.role) {
      case 'student':
        return <Navigate to="/student" replace />
      case 'instructor':
        return <Navigate to="/instructor" replace />
      case 'admin':
        return <Navigate to="/head" replace />
      default:
        return <Navigate to="/login" replace />
    }
  }

  return (
    <div>
      {getRoleBasedDashboard()}
    </div>
  )
}

export default Dashboard
