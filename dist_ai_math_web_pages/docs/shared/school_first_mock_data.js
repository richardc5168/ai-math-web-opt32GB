(function () {
  function buildStudent(teacherIndex, studentIndex) {
    const absoluteIndex = (teacherIndex - 1) * 58 + studentIndex;
    const band = ['high', 'mid', 'low'][(absoluteIndex - 1) % 3];
    const pre = band === 'high' ? 0.68 : band === 'mid' ? 0.48 : 0.31;
    const post = band === 'high' ? 0.86 : band === 'mid' ? 0.63 : 0.29;
    const risk = band === 'low' ? 92 - (studentIndex % 11) : band === 'mid' ? 61 - (studentIndex % 9) : 25 - (studentIndex % 5);
    return {
      student_id: `student-${String(absoluteIndex).padStart(3, '0')}`,
      display_name: `Student ${String(absoluteIndex).padStart(3, '0')}`,
      parent_name: `Parent ${String(absoluteIndex).padStart(3, '0')}`,
      grade: teacherIndex === 1 ? 'G5' : 'G6',
      band,
      risk_score: risk,
      pre_accuracy: pre,
      post_accuracy: post,
      delta: +(post - pre).toFixed(2),
      weak_skills: band === 'low' ? ['fraction_add', 'word_multi'] : band === 'mid' ? ['ratio_reasoning'] : ['decimal_place'],
      next_action: band === 'low' ? 'Assign small-group reteach and parent follow-up.' : band === 'mid' ? 'Targeted ratio practice.' : 'Advance with challenge set.',
    };
  }

  function buildClass(teacherIndex, teacherName, className) {
    const students = [];
    for (let i = 1; i <= 58; i += 1) students.push(buildStudent(teacherIndex, i));
    const improved = students.filter((x) => x.delta >= 0.15).length;
    const flat = students.filter((x) => x.delta > -0.15 && x.delta < 0.15).length;
    const regressed = students.filter((x) => x.delta <= -0.15).length;
    return {
      class_id: `class-${String(teacherIndex).padStart(3, '0')}`,
      teacher_id: `teacher-${String(teacherIndex).padStart(3, '0')}`,
      teacher_name: teacherName,
      class_name: className,
      students,
      summary: {
        student_count: students.length,
        improved,
        flat,
        regressed,
        pre_accuracy: +(students.reduce((a, b) => a + b.pre_accuracy, 0) / students.length).toFixed(2),
        post_accuracy: +(students.reduce((a, b) => a + b.post_accuracy, 0) / students.length).toFixed(2),
      },
      intervention: {
        title: 'Fraction and multi-step reteach',
        target_skills: ['fraction_add', 'word_multi'],
        method: 'Small group + exit ticket + parent follow-up',
      },
    };
  }

  /* R50: mock hint summary matching format_hint_summary_for_teacher() shape */
  function buildHintSummary() {
    return {
      overview: {
        total_hinted_attempts: 87,
        hint_success_rate: 0.62,
        hint_success_rate_pct: '62%',
        stuck_after_hint_rate: 0.38,
        stuck_after_hint_rate_pct: '38%',
        avg_hints_before_success: 1.8,
        hint_escalation_rate: 0.31,
        hint_escalation_rate_pct: '31%',
        avg_hint_dwell_ms: 4500,
        avg_hint_dwell_sec: 4.5,
        evidence_chain_complete_rate: 0.85,
        evidence_chain_complete_rate_pct: '85%',
        hint_level_used_coverage_rate_pct: '92%',
        hint_sequence_coverage_rate_pct: '88%',
        hint_open_ts_coverage_rate_pct: '85%',
      },
      by_level: [
        { hint_count: '1', label: '看了 1 個提示', attempts: 45, correct: 32, success_rate_pct: '71%' },
        { hint_count: '2', label: '看了 2 個提示', attempts: 28, correct: 16, success_rate_pct: '57%' },
        { hint_count: '3', label: '看了 3 個提示', attempts: 14, correct: 6, success_rate_pct: '43%' },
      ],
      recommendations: [
        '提示整體有效率 62%，學生使用提示後多數能答對。',
        '目前提示 evidence chain 完整率為 85%，建議持續補齊 telemetry 以提升比較可信度。',
      ],
      risk_flags: [
        '⚠ 31% 的提示作答升級到較高提示層級，可能代表學生在基礎理解前就需要較重支援。',
      ],
    };
  }

  function buildFixture() {
    const classes = [
      buildClass(1, 'Teacher Hsu', 'Class 5A'),
      buildClass(2, 'Teacher Lin', 'Class 6B'),
    ];
    const parents = classes.flatMap((cls) => cls.students.map((student) => ({
      parent_id: student.student_id.replace('student', 'parent'),
      parent_name: student.parent_name,
      student_id: student.student_id,
      child_summary: {
        display_name: student.display_name,
        pre_accuracy: student.pre_accuracy,
        post_accuracy: student.post_accuracy,
        delta: student.delta,
        weak_skills: student.weak_skills,
        support_actions: [
          'Review one weak skill for 10 minutes after dinner.',
          'Ask the child to explain one solved example aloud.',
        ],
      },
    })));
    return {
      admin: { display_name: 'System Owner' },
      classes,
      parents,
      admin_rollup: {
        teacher_count: 2,
        student_count: 116,
        improved_count: classes.reduce((sum, cls) => sum + cls.summary.improved, 0),
        flat_count: classes.reduce((sum, cls) => sum + cls.summary.flat, 0),
        regressed_count: classes.reduce((sum, cls) => sum + cls.summary.regressed, 0),
      },
    };
  }

  window.AIMathSchoolFirstMockData = { buildFixture, buildHintSummary };
})();