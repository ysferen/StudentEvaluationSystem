import { Navigate } from 'react-router-dom'
import { useAuth } from '../../auth/hooks/useAuth'
import Navbar from '../components/Navbar'
import HeroSection from '../components/HeroSection'
import FeaturesSection from '../components/FeaturesSection'
import HowItWorksSection from '../components/HowItWorksSection'
import RoleCardsSection from '../components/RoleCardsSection'
import LiveStatsSection from '../components/LiveStatsSection'
import CTASection from '../components/CTASection'
import Footer from '../components/Footer'

const LandingPage = () => {
  const { isAuthenticated, user } = useAuth()

  if (isAuthenticated && user) {
    const rolePath = user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : user.role === 'student' ? '/student' : '/login'
    return <Navigate to={rolePath} replace />
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <RoleCardsSection />
      <LiveStatsSection />
      <CTASection />
      <Footer />
    </div>
  )
}

export default LandingPage
