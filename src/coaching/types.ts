export type Grade = 5;

export type G5Unit = 'fraction' | 'decimal' | 'ratio' | 'life';

export type ErrorType = 'calc' | 'reading' | 'concept' | 'strategy' | 'unknown';

export type HintLevel = 1 | 2 | 3;

export interface HintStep {
  level: HintLevel;
  title: string;
  body: string;
}

export interface CommonMistake {
  type: Exclude<ErrorType, 'unknown'>;
  message: string;
  fix: string;
}

export interface CoachingMeta {
  question_id: string;
  grade: Grade;
  unit: G5Unit;
  skill_tags: string[];
  hint_ladder: HintStep[];
  common_mistakes: CommonMistake[];
  similar_question_ids: string[];
}

export type CoachingMetaFile = CoachingMeta[];

export interface CoachingEventBase {
  ts: string; // ISO string
  user_id: string;
  question_id: string;
  unit: G5Unit;
  skill_tags: string[];
}

export type CoachingEvent =
  | (CoachingEventBase & { type: 'attempt_started' })
  | (CoachingEventBase & { type: 'hint_shown'; level: HintLevel })
  | (CoachingEventBase & {
      type: 'answer_submitted';
      user_answer: string;
      expected_answer?: string;
      allow_continue?: boolean;
    })
  | (CoachingEventBase & {
      type: 'attempt_completed';
      is_correct: boolean;
      duration_ms: number;
      hint_levels_used: HintLevel[];
      error_type: ErrorType;
      allow_continue?: boolean;
    });
