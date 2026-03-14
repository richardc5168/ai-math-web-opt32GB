# Iteration Report — 2026-03-14

## 本輪修改內容
Iteration 9: Equivalent mutation detection + unit_conversion quality hardening. Added equivalent mutation detector (flags mutations producing same answer as original). Added value_one_reverse_trivial check. Overall mutation kill rate 47.5%% -> 64.2%%.

## 新增測試數量: 0

## 總 Pass Rate: 120/120 (100.0%)

## 各題型 Pass Rate
| 題型 | Pass | Total | Rate |
|------|------|-------|------|
| average_word_problem | 30 | 30 | 100.0% |
| decimal_word_problem | 30 | 30 | 100.0% |
| fraction_word_problem | 30 | 30 | 100.0% |
| unit_conversion | 30 | 30 | 100.0% |

## Benchmark 覆蓋分布
### pattern_type
| 類型 | 數量 |
|------|------|
| adversarial | 16 |
| boundary | 16 |
| edge | 16 |
| normal | 56 |
| wording_variation | 16 |

### risk_level
| 等級 | 數量 |
|------|------|
| high | 19 |
| low | 58 |
| medium | 43 |

## 新發現錯誤類型
（無）

## 已解決錯誤類型
（無）

## Risk-Based Sampling
- 需人工審查: 8/120 (6.7%)
- 自動信任: 112/120 (93.3%)
- 理論節省人力: 93%

| 題型 | Low | Medium | High |
|------|-----|--------|------|
| average_word_problem | 29 | 1 | 0 |
| decimal_word_problem | 30 | 0 | 0 |
| fraction_word_problem | 23 | 7 | 0 |
| unit_conversion | 22 | 8 | 0 |

## Fail Clustering
- ✅ 無失敗群集

## 建議下一輪優先修正項目
- 全部通過，可考慮增加更多 benchmark cases

## 是否值得升級為 Gold Sample
✅ 全部通過，建議將新增 cases 納入 gold_bank。
