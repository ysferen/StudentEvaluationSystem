export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'guest' | 'student' | 'instructor' | 'department_head' | 'admin';
  staff_id?: string;
  student_id?: string;
  department?: string;
}

export interface University {
  id: number
  name: string
  code: string
}

export interface Department {
  id: number
  name: string
  code: string
  university: number
}

export interface Program {
  id: number;
  name: string;
  code: string;
  department: number; // Added department field
  description: string;
  duration_years: number;
  total_credits: number;
  created_at: string;
  updated_at: string;
}

export interface ProgramOutcome {
  id: number;
  program: number;
  code: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: number;
  program?: number;
  code: string;
  name: string;
  description?: string;
  credits: number;
  level?: 'undergraduate' | 'graduate';
  year?: number;
  semester?: 'fall' | 'spring' | 'summer';
  lecturer?: User;
  department?: {
    id: number;
    name: string;
    code: string;
  };
  term?: {
    id: number;
    name: string;
    is_active: boolean;
  };
  instructors?: User[];
  created_at?: string;
  updated_at?: string;
  course_analytics?: CourseAnalytics;
}

export interface LearningOutcome {
  id: number;
  code: string;
  description: string;
  course: number;
  created_by?: number;
  created_at: string;
  updated_at: string;
}

export interface Assessment {
  id: number;
  title: string;
  description?: string;
  course: number;
  max_score: number;
  weight: number;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: number
  student: number
  course: Course
  term: number
  grade?: string
}

export interface LearningOutcomeScore {
  id: number
  student: number
  learning_outcome: {
    id: number
    code: string
    description: string
    course: {
      id: number
      code: string
      name: string
    }
  }
  score: number
}

export interface ProgramOutcomeScore {
  id: number
  student: number
  program_outcome: {
    id: number
    code: string
    description: string
  }
  score: number
}

export interface CourseAverage {
  course_id: number
  weighted_average: number | null
}

export interface CourseOutcome {
  id: number;
  course: number;
  code: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface OutcomeMapping {
  id: number;
  course_outcome: number;
  program_outcome: number;
  strength: number; // 1-5 scale
  created_at: string;
  updated_at: string;
}

export interface Assignment {
  id: number;
  course: number;
  title: string;
  description: string;
  due_date: string;
  max_score: number;
  weight: number;
  created_at: string;
  updated_at: string;
  assignment_analytics?: AssignmentAnalytics;
}

export interface Submission {
  id: number;
  assignment: number;
  student: User;
  submitted_at: string;
  is_late: boolean;
  status: 'submitted' | 'graded' | 'not_submitted';
}

export interface Score {
  id: number;
  submission: number;
  course_outcome: number;
  score: number;
  max_score: number;
  feedback?: string;
  created_at: string;
  updated_at: string;
}

export interface OutcomeAchievement {
  id: number;
  student: User;
  program_outcome: number;
  course_outcome: number;
  achievement_level: number; // 0-100 percentage
  created_at: string;
  updated_at: string;
}

export interface CourseAnalytics {
  total_students: number;
  average_score: number;
  outcome_averages: Record<number, number>;
  assignment_completion_rate: number;
}

export interface AssignmentAnalytics {
  total_submissions: number;
  average_score: number;
  outcome_averages: Record<number, number>;
  late_submission_rate: number;
}

export interface StudentAnalytics {
  overall_achievement: number;
  outcome_achievements: Record<number, number>;
  assignment_performance: Array<{
    assignment: number;
    score: number;
    class_average: number;
  }>;
  progress_trajectory: Array<{
    date: string;
    achievement: number;
  }>;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}
