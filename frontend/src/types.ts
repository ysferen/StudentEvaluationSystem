export interface User {
    id: number
    username: string
    email: string
    role: 'student' | 'instructor' | 'department_head' | 'admin'
    first_name: string
    last_name: string
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
    id: number
    name: string
    code: string
    department: number
}

export interface Course {
    id: number
    name: string
    code: string
    program: number
    credits: number
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
