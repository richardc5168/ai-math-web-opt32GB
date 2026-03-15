# Iteration Report — 2026-03-15

## 本輪修改內容
(first full cycle run)

## 新增測試數量: 0

## 總 Pass Rate: 160/160 (100.0%)

## 各題型 Pass Rate
| 題型 | Pass | Total | Rate |
|------|------|-------|------|
| average_word_problem | 40 | 40 | 100.0% |
| decimal_word_problem | 40 | 40 | 100.0% |
| fraction_word_problem | 40 | 40 | 100.0% |
| unit_conversion | 40 | 40 | 100.0% |

## Benchmark 覆蓋分布
### pattern_type
| 類型 | 數量 |
|------|------|
| adversarial | 27 |
| boundary | 29 |
| edge | 25 |
| normal | 56 |
| wording_variation | 23 |

### risk_level
| 等級 | 數量 |
|------|------|
| high | 30 |
| low | 60 |
| medium | 70 |

## 新發現錯誤類型
（無）

## 已解決錯誤類型
（無）

## Risk-Based Sampling
- 需人工審查: 10/160 (6.2%)
- 自動信任: 150/160 (93.8%)
- 理論節省人力: 94%

| 題型 | Low | Medium | High |
|------|-----|--------|------|
| average_word_problem | 39 | 1 | 0 |
| decimal_word_problem | 34 | 6 | 0 |
| fraction_word_problem | 33 | 7 | 0 |
| unit_conversion | 28 | 12 | 0 |

## Fail Clustering
- ✅ 無失敗群集

## 建議下一輪優先修正項目
- 全部通過，可考慮增加更多 benchmark cases

## 是否值得升級為 Gold Sample
✅ 全部通過，建議將新增 cases 納入 gold_bank。
