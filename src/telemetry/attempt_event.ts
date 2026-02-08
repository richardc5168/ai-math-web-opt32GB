export type JudgeType = 'numeric' | 'fraction' | 'expr' | 'sympy' | 'regex';

export type AttemptEvent = {
  attempt_id: string;
  user_id: string;
  session_id: string;
  ts_start: number; // ms
  ts_end: number; // ms

  pack_id?: string;
  module_id: string; // e.g. interactive-g5-empire, coach
  unit_id?: string;
  kind: string;
  topic_tags: string[];
  difficulty?: string;

  question_id: string;
  correct_answer?: string; // optional: can store hash instead
  user_answer: string;

  is_correct: boolean;
  judge_type: JudgeType;
  attempts_count: number;

  hint: {
    shown_levels: number[]; // e.g. [1,2]
    shown_count: number;
    first_shown_at?: number;
    total_hint_ms: number;
  };

  steps: {
    used_next_step: boolean;
    shown_solution: boolean;
  };

  device?: { platform?: string; ua?: string };
};

export type AttemptLogFile = {
  version: 1;
  user_id: string;
  attempts: AttemptEvent[];
};
