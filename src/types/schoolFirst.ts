export type Role = 'parent' | 'teacher' | 'admin' | 'student';

export type QuestionMetadata = {
  question_id: string;
  topic: string;
  subtopic: string;
  skill_tag: string;
  knowledge_point: string;
  difficulty: number;
  pattern_type: string;
  equivalent_group_id: string;
};

export type AnswerRecord = {
  assessment_id: string;
  student_id: string;
  class_id: string;
  question_id: string;
  answer: string;
  correctness: boolean;
  response_time: number;
  hint_used: boolean;
  attempt_count: number;
  error_type: string;
  timestamp: string;
};

export type InterventionRecord = {
  intervention_id: string;
  class_id: string;
  teacher_id: string;
  date: string;
  target_students: string[];
  target_skills: string[];
  teaching_method: string;
  notes: string;
  linked_pretest_id: string;
  linked_posttest_id: string;
};

export type Assessment = {
  assessment_id: string;
  student_id: string;
  class_id: string;
  assessment_type: 'pre_test' | 'post_test';
  assigned_at: string;
  completed_at: string;
};

export type StudentProfile = {
  student_id: string;
  class_id: string;
  parent_id: string;
  teacher_id: string;
  display_name: string;
  grade: string;
  band: 'high' | 'mid' | 'low';
};

export type SchoolFirstFixture = {
  admin: { admin_id: string; display_name: string };
  teachers: Array<{ teacher_id: string; display_name: string; class_id: string }>;
  parents: Array<{ parent_id: string; student_id: string; display_name: string }>;
  students: StudentProfile[];
  assessments: Assessment[];
  interventions: InterventionRecord[];
  question_metadata: QuestionMetadata[];
  answer_records: AnswerRecord[];
};