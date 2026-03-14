# Mutation Testing Report

## Summary

| Metric | Value |
|--------|-------|
| Total mutations | 135 |
| Killed (detected) | 107 |
| Survived (undetected) | 28 |
| Mutation score | 79.3% |

## Per-Topic Results

| Topic | Killed | Survived | Total | Score |
|-------|--------|----------|-------|-------|
| average_word_problem | 25 | 0 | 25 | 100.0% |
| decimal_word_problem | 19 | 6 | 25 | 76.0% |
| fraction_word_problem | 43 | 12 | 55 | 78.2% |
| unit_conversion | 20 | 10 | 30 | 66.7% |

## Surviving Mutations (Weaknesses)

These mutations were NOT detected — potential blind spots:

| Case | Mutation | Notes |
|------|----------|-------|
| fraction_word_problem[0] | b_den_minus1 | survived |
| fraction_word_problem[0] | template_shift | survived |
| fraction_word_problem[1] | a_den_plus1 | survived |
| fraction_word_problem[1] | b_den_minus1 | survived |
| fraction_word_problem[1] | equal_fractions | survived |
| fraction_word_problem[1] | template_shift | survived |
| fraction_word_problem[2] | b_den_minus1 | survived |
| fraction_word_problem[2] | b_den_plus1 | survived |
| fraction_word_problem[2] | template_shift | survived |
| fraction_word_problem[3] | a_den_plus1 | survived |
| fraction_word_problem[3] | b_den_plus1 | survived |
| fraction_word_problem[4] | large_denoms | survived |
| decimal_word_problem[0] | template_shift | survived |
| decimal_word_problem[1] | equal_operands | survived |
| decimal_word_problem[2] | template_shift | survived |
| decimal_word_problem[3] | equal_operands | survived |
| decimal_word_problem[3] | template_shift | survived |
| decimal_word_problem[4] | equal_operands | survived |
| unit_conversion[0] | direction_flip | survived |
| unit_conversion[0] | decimal_value | survived |
| ... | +8 more | |

## Gold Bank Promotion Candidates

Cases with high mutation kill rates (robust validations):

| Case | Kill Rate | Tested | Killed |
|------|-----------|--------|--------|
| average_word_problem[0] | 100% | 5 | 5 |
| average_word_problem[1] | 100% | 5 | 5 |
| average_word_problem[2] | 100% | 5 | 5 |
| average_word_problem[3] | 100% | 5 | 5 |
| average_word_problem[4] | 100% | 5 | 5 |
| fraction_word_problem[4] | 91% | 11 | 10 |
| fraction_word_problem[0] | 82% | 11 | 9 |
| fraction_word_problem[3] | 82% | 11 | 9 |
| decimal_word_problem[0] | 80% | 5 | 4 |
| decimal_word_problem[1] | 80% | 5 | 4 |
