# Mutation Testing Report

## Summary

| Metric | Value |
|--------|-------|
| Total mutations | 120 |
| Killed (detected) | 77 |
| Survived (undetected) | 43 |
| Mutation score | 64.2% |

## Per-Topic Results

| Topic | Killed | Survived | Total | Score |
|-------|--------|----------|-------|-------|
| average_word_problem | 21 | 4 | 25 | 84.0% |
| decimal_word_problem | 19 | 6 | 25 | 76.0% |
| fraction_word_problem | 19 | 21 | 40 | 47.5% |
| unit_conversion | 18 | 12 | 30 | 60.0% |

## Surviving Mutations (Weaknesses)

These mutations were NOT detected — potential blind spots:

| Case | Mutation | Notes |
|------|----------|-------|
| fraction_word_problem[0] | a_den_plus1 | survived |
| fraction_word_problem[0] | b_den_minus1 | survived |
| fraction_word_problem[0] | b_den_plus1 | survived |
| fraction_word_problem[0] | large_denoms | survived |
| fraction_word_problem[0] | template_shift | survived |
| fraction_word_problem[1] | a_den_plus1 | survived |
| fraction_word_problem[1] | b_den_minus1 | survived |
| fraction_word_problem[1] | b_den_plus1 | survived |
| fraction_word_problem[1] | equal_fractions | survived |
| fraction_word_problem[1] | large_denoms | survived |
| fraction_word_problem[1] | template_shift | survived |
| fraction_word_problem[2] | a_den_plus1 | survived |
| fraction_word_problem[2] | b_den_minus1 | survived |
| fraction_word_problem[2] | b_den_plus1 | survived |
| fraction_word_problem[2] | large_denoms | survived |
| fraction_word_problem[2] | template_shift | survived |
| fraction_word_problem[3] | a_den_plus1 | survived |
| fraction_word_problem[3] | b_den_plus1 | survived |
| fraction_word_problem[3] | large_denoms | survived |
| fraction_word_problem[4] | b_den_plus1 | survived |
| ... | +23 more | |

## Gold Bank Promotion Candidates

Cases with high mutation kill rates (robust validations):

| Case | Kill Rate | Tested | Killed |
|------|-----------|--------|--------|
| average_word_problem[4] | 100% | 5 | 5 |
| decimal_word_problem[0] | 80% | 5 | 4 |
| decimal_word_problem[1] | 80% | 5 | 4 |
| decimal_word_problem[2] | 80% | 5 | 4 |
| decimal_word_problem[4] | 80% | 5 | 4 |
| average_word_problem[0] | 80% | 5 | 4 |
| average_word_problem[1] | 80% | 5 | 4 |
| average_word_problem[2] | 80% | 5 | 4 |
| average_word_problem[3] | 80% | 5 | 4 |
