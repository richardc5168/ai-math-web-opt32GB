/* Auto-generated from math-offline gold_bank.jsonl (vendored). */
window.OFFLINE_MATH_BANK = [
  {
    "id": "offline_time-001",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_ratio",
    "params": {
      "aDays": 4,
      "aHours": 15,
      "bDays": 1,
      "bHours": 13
    },
    "prompt": "4日15時 ÷ 1日13時 = ?",
    "answer": {
      "q": 3
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把兩個時間都換成同一單位（通常換成『小時』或『秒』），再相除。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "把 4日15時 換成小時：4×24+15=111",
        "expr": "4*24+15",
        "value": "111",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 1日13時 換成小時：1×24+13=37",
        "expr": "1*24+13",
        "value": "37",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "再相除：111 ÷ 37 = 3",
        "expr": "111/37",
        "value": "3",
        "unit": "倍"
      },
      {
        "k": "result",
        "say": "所以答案是 3 倍。",
        "value": "3",
        "unit": "倍"
      },
      {
        "k": "check",
        "say": "檢查：37×3 = 111（要剛好相等才是整除）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.085Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-002",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_mul_day_hour",
    "params": {
      "days": 2,
      "hours": 19,
      "n": 8
    },
    "prompt": "2日19時 × 8 = ?",
    "answer": {
      "outDays": 22,
      "outHours": 8
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把『日』和『時』分開乘，最後再把小時進位成天。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "先算天：2日×8=16日",
        "expr": "2*8",
        "value": "16",
        "unit": "日"
      },
      {
        "k": "compute",
        "say": "再算時：19時×8=152時",
        "expr": "19*8",
        "value": "152",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 152 時換成天和時：152 ÷ 24 = 6 天…剩 8 時",
        "expr": "152 div 24",
        "value": "6",
        "unit": "日"
      },
      {
        "k": "result",
        "say": "合併：16日+6日=22日，還有 8時。"
      },
      {
        "k": "check",
        "say": "檢查：最後的小時一定要小於 24（8 < 24）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.086Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-003",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_seconds",
    "params": {
      "min": 11,
      "sec": 26,
      "divSec": 49
    },
    "prompt": "11分26秒 ÷ 49秒 = ?",
    "answer": {
      "q": 14
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把時間統一成『秒』，才好做除法。"
      },
      {
        "k": "formula",
        "say": "1 分 = 60 秒。"
      },
      {
        "k": "compute",
        "say": "把 11分26秒 變成秒：11×60+26",
        "expr": "11*60+26",
        "value": "686",
        "unit": "秒"
      },
      {
        "k": "compute",
        "say": "再做除法：686 ÷ 49",
        "expr": "floor(686/49)",
        "value": "14",
        "unit": "次"
      },
      {
        "k": "result",
        "say": "所以一共可以做 14 次。",
        "value": "14",
        "unit": "次"
      },
      {
        "k": "check",
        "say": "檢查：14×49 = 686 秒，不能超過 686 秒。",
        "expr": "14*49",
        "value": "686",
        "unit": "秒"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.086Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-004",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_seconds",
    "params": {
      "min": 6,
      "sec": 56,
      "divSec": 26
    },
    "prompt": "6分56秒 ÷ 26秒 = ?",
    "answer": {
      "q": 16
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把時間統一成『秒』，才好做除法。"
      },
      {
        "k": "formula",
        "say": "1 分 = 60 秒。"
      },
      {
        "k": "compute",
        "say": "把 6分56秒 變成秒：6×60+56",
        "expr": "6*60+56",
        "value": "416",
        "unit": "秒"
      },
      {
        "k": "compute",
        "say": "再做除法：416 ÷ 26",
        "expr": "floor(416/26)",
        "value": "16",
        "unit": "次"
      },
      {
        "k": "result",
        "say": "所以一共可以做 16 次。",
        "value": "16",
        "unit": "次"
      },
      {
        "k": "check",
        "say": "檢查：16×26 = 416 秒，不能超過 416 秒。",
        "expr": "16*26",
        "value": "416",
        "unit": "秒"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.087Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-005",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_ratio",
    "params": {
      "aDays": 3,
      "aHours": 2,
      "bDays": 1,
      "bHours": 13
    },
    "prompt": "3日2時 ÷ 1日13時 = ?",
    "answer": {
      "q": 2
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把兩個時間都換成同一單位（通常換成『小時』或『秒』），再相除。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "把 3日2時 換成小時：3×24+2=74",
        "expr": "3*24+2",
        "value": "74",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 1日13時 換成小時：1×24+13=37",
        "expr": "1*24+13",
        "value": "37",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "再相除：74 ÷ 37 = 2",
        "expr": "74/37",
        "value": "2",
        "unit": "倍"
      },
      {
        "k": "result",
        "say": "所以答案是 2 倍。",
        "value": "2",
        "unit": "倍"
      },
      {
        "k": "check",
        "say": "檢查：37×2 = 74（要剛好相等才是整除）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.087Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-006",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_mul_day_hour",
    "params": {
      "days": 2,
      "hours": 12,
      "n": 7
    },
    "prompt": "2日12時 × 7 = ?",
    "answer": {
      "outDays": 17,
      "outHours": 12
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把『日』和『時』分開乘，最後再把小時進位成天。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "先算天：2日×7=14日",
        "expr": "2*7",
        "value": "14",
        "unit": "日"
      },
      {
        "k": "compute",
        "say": "再算時：12時×7=84時",
        "expr": "12*7",
        "value": "84",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 84 時換成天和時：84 ÷ 24 = 3 天…剩 12 時",
        "expr": "84 div 24",
        "value": "3",
        "unit": "日"
      },
      {
        "k": "result",
        "say": "合併：14日+3日=17日，還有 12時。"
      },
      {
        "k": "check",
        "say": "檢查：最後的小時一定要小於 24（12 < 24）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.087Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-007",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_mul_day_hour",
    "params": {
      "days": 5,
      "hours": 6,
      "n": 12
    },
    "prompt": "5日6時 × 12 = ?",
    "answer": {
      "outDays": 63,
      "outHours": 0
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把『日』和『時』分開乘，最後再把小時進位成天。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "先算天：5日×12=60日",
        "expr": "5*12",
        "value": "60",
        "unit": "日"
      },
      {
        "k": "compute",
        "say": "再算時：6時×12=72時",
        "expr": "6*12",
        "value": "72",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 72 時換成天和時：72 ÷ 24 = 3 天…剩 0 時",
        "expr": "72 div 24",
        "value": "3",
        "unit": "日"
      },
      {
        "k": "result",
        "say": "合併：60日+3日=63日，還有 0時。"
      },
      {
        "k": "check",
        "say": "檢查：最後的小時一定要小於 24（0 < 24）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.087Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-008",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_mul_day_hour",
    "params": {
      "days": 6,
      "hours": 11,
      "n": 12
    },
    "prompt": "6日11時 × 12 = ?",
    "answer": {
      "outDays": 77,
      "outHours": 12
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把『日』和『時』分開乘，最後再把小時進位成天。"
      },
      {
        "k": "formula",
        "say": "1 日 = 24 時。"
      },
      {
        "k": "compute",
        "say": "先算天：6日×12=72日",
        "expr": "6*12",
        "value": "72",
        "unit": "日"
      },
      {
        "k": "compute",
        "say": "再算時：11時×12=132時",
        "expr": "11*12",
        "value": "132",
        "unit": "時"
      },
      {
        "k": "compute",
        "say": "把 132 時換成天和時：132 ÷ 24 = 5 天…剩 12 時",
        "expr": "132 div 24",
        "value": "5",
        "unit": "日"
      },
      {
        "k": "result",
        "say": "合併：72日+5日=77日，還有 12時。"
      },
      {
        "k": "check",
        "say": "檢查：最後的小時一定要小於 24（12 < 24）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.088Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-009",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_seconds",
    "params": {
      "min": 4,
      "sec": 57,
      "divSec": 27
    },
    "prompt": "4分57秒 ÷ 27秒 = ?",
    "answer": {
      "q": 11
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把時間統一成『秒』，才好做除法。"
      },
      {
        "k": "formula",
        "say": "1 分 = 60 秒。"
      },
      {
        "k": "compute",
        "say": "把 4分57秒 變成秒：4×60+57",
        "expr": "4*60+57",
        "value": "297",
        "unit": "秒"
      },
      {
        "k": "compute",
        "say": "再做除法：297 ÷ 27",
        "expr": "floor(297/27)",
        "value": "11",
        "unit": "次"
      },
      {
        "k": "result",
        "say": "所以一共可以做 11 次。",
        "value": "11",
        "unit": "次"
      },
      {
        "k": "check",
        "say": "檢查：11×27 = 297 秒，不能超過 297 秒。",
        "expr": "11*27",
        "value": "297",
        "unit": "秒"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.088Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_time-010",
    "grade": 5,
    "topic": "time_calc",
    "type": "time_div_seconds",
    "params": {
      "min": 4,
      "sec": 48,
      "divSec": 24
    },
    "prompt": "4分48秒 ÷ 24秒 = ?",
    "answer": {
      "q": 12
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先把時間統一成『秒』，才好做除法。"
      },
      {
        "k": "formula",
        "say": "1 分 = 60 秒。"
      },
      {
        "k": "compute",
        "say": "把 4分48秒 變成秒：4×60+48",
        "expr": "4*60+48",
        "value": "288",
        "unit": "秒"
      },
      {
        "k": "compute",
        "say": "再做除法：288 ÷ 24",
        "expr": "floor(288/24)",
        "value": "12",
        "unit": "次"
      },
      {
        "k": "result",
        "say": "所以一共可以做 12 次。",
        "value": "12",
        "unit": "次"
      },
      {
        "k": "check",
        "say": "檢查：12×24 = 288 秒，不能超過 288 秒。",
        "expr": "12*24",
        "value": "288",
        "unit": "秒"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.088Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-001",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 4149,
      "divisor": 31
    },
    "prompt": "4149 ÷ 31 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 133,
      "r": 26
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 4 裡有幾個 31：取 0",
        "expr": "floor(4/31)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×31=0，4−0=4",
        "expr": "4-0*31",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "把下一位 1 拉下來，變成 41。"
      },
      {
        "k": "compute",
        "say": "看 41 裡有幾個 31：取 1",
        "expr": "floor(41/31)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×31=31，41−31=10",
        "expr": "41-1*31",
        "value": "10"
      },
      {
        "k": "compute",
        "say": "把下一位 4 拉下來，變成 104。"
      },
      {
        "k": "compute",
        "say": "看 104 裡有幾個 31：取 3",
        "expr": "floor(104/31)",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "3×31=93，104−93=11",
        "expr": "104-3*31",
        "value": "11"
      },
      {
        "k": "compute",
        "say": "把下一位 9 拉下來，變成 119。"
      },
      {
        "k": "compute",
        "say": "看 119 裡有幾個 31：取 3",
        "expr": "floor(119/31)",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "3×31=93，119−93=26",
        "expr": "119-3*31",
        "value": "26"
      },
      {
        "k": "result",
        "say": "所以商是 133，餘數是 26。",
        "value": "133"
      },
      {
        "k": "check",
        "say": "驗算：31×133+26=4149（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.089Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-002",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 1515,
      "divisor": 11
    },
    "prompt": "1515 ÷ 11 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 137,
      "r": 8
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 1 裡有幾個 11：取 0",
        "expr": "floor(1/11)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×11=0，1−0=1",
        "expr": "1-0*11",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "把下一位 5 拉下來，變成 15。"
      },
      {
        "k": "compute",
        "say": "看 15 裡有幾個 11：取 1",
        "expr": "floor(15/11)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×11=11，15−11=4",
        "expr": "15-1*11",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "把下一位 1 拉下來，變成 41。"
      },
      {
        "k": "compute",
        "say": "看 41 裡有幾個 11：取 3",
        "expr": "floor(41/11)",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "3×11=33，41−33=8",
        "expr": "41-3*11",
        "value": "8"
      },
      {
        "k": "compute",
        "say": "把下一位 5 拉下來，變成 85。"
      },
      {
        "k": "compute",
        "say": "看 85 裡有幾個 11：取 7",
        "expr": "floor(85/11)",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "7×11=77，85−77=8",
        "expr": "85-7*11",
        "value": "8"
      },
      {
        "k": "result",
        "say": "所以商是 137，餘數是 8。",
        "value": "137"
      },
      {
        "k": "check",
        "say": "驗算：11×137+8=1515（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.089Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-003",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 7747,
      "divisor": 47
    },
    "prompt": "7747 ÷ 47 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 164,
      "r": 39
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 7 裡有幾個 47：取 0",
        "expr": "floor(7/47)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×47=0，7−0=7",
        "expr": "7-0*47",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 77。"
      },
      {
        "k": "compute",
        "say": "看 77 裡有幾個 47：取 1",
        "expr": "floor(77/47)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×47=47，77−47=30",
        "expr": "77-1*47",
        "value": "30"
      },
      {
        "k": "compute",
        "say": "把下一位 4 拉下來，變成 304。"
      },
      {
        "k": "compute",
        "say": "看 304 裡有幾個 47：取 6",
        "expr": "floor(304/47)",
        "value": "6"
      },
      {
        "k": "compute",
        "say": "6×47=282，304−282=22",
        "expr": "304-6*47",
        "value": "22"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 227。"
      },
      {
        "k": "compute",
        "say": "看 227 裡有幾個 47：取 4",
        "expr": "floor(227/47)",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "4×47=188，227−188=39",
        "expr": "227-4*47",
        "value": "39"
      },
      {
        "k": "result",
        "say": "所以商是 164，餘數是 39。",
        "value": "164"
      },
      {
        "k": "check",
        "say": "驗算：47×164+39=7747（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.090Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-004",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 5710,
      "divisor": 21
    },
    "prompt": "5710 ÷ 21 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 271,
      "r": 19
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 5 裡有幾個 21：取 0",
        "expr": "floor(5/21)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×21=0，5−0=5",
        "expr": "5-0*21",
        "value": "5"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 57。"
      },
      {
        "k": "compute",
        "say": "看 57 裡有幾個 21：取 2",
        "expr": "floor(57/21)",
        "value": "2"
      },
      {
        "k": "compute",
        "say": "2×21=42，57−42=15",
        "expr": "57-2*21",
        "value": "15"
      },
      {
        "k": "compute",
        "say": "把下一位 1 拉下來，變成 151。"
      },
      {
        "k": "compute",
        "say": "看 151 裡有幾個 21：取 7",
        "expr": "floor(151/21)",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "7×21=147，151−147=4",
        "expr": "151-7*21",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "把下一位 0 拉下來，變成 40。"
      },
      {
        "k": "compute",
        "say": "看 40 裡有幾個 21：取 1",
        "expr": "floor(40/21)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×21=21，40−21=19",
        "expr": "40-1*21",
        "value": "19"
      },
      {
        "k": "result",
        "say": "所以商是 271，餘數是 19。",
        "value": "271"
      },
      {
        "k": "check",
        "say": "驗算：21×271+19=5710（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.090Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-005",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 3934,
      "divisor": 22
    },
    "prompt": "3934 ÷ 22 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 178,
      "r": 18
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 3 裡有幾個 22：取 0",
        "expr": "floor(3/22)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×22=0，3−0=3",
        "expr": "3-0*22",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "把下一位 9 拉下來，變成 39。"
      },
      {
        "k": "compute",
        "say": "看 39 裡有幾個 22：取 1",
        "expr": "floor(39/22)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×22=22，39−22=17",
        "expr": "39-1*22",
        "value": "17"
      },
      {
        "k": "compute",
        "say": "把下一位 3 拉下來，變成 173。"
      },
      {
        "k": "compute",
        "say": "看 173 裡有幾個 22：取 7",
        "expr": "floor(173/22)",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "7×22=154，173−154=19",
        "expr": "173-7*22",
        "value": "19"
      },
      {
        "k": "compute",
        "say": "把下一位 4 拉下來，變成 194。"
      },
      {
        "k": "compute",
        "say": "看 194 裡有幾個 22：取 8",
        "expr": "floor(194/22)",
        "value": "8"
      },
      {
        "k": "compute",
        "say": "8×22=176，194−176=18",
        "expr": "194-8*22",
        "value": "18"
      },
      {
        "k": "result",
        "say": "所以商是 178，餘數是 18。",
        "value": "178"
      },
      {
        "k": "check",
        "say": "驗算：22×178+18=3934（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.090Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-006",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 3083,
      "divisor": 21
    },
    "prompt": "3083 ÷ 21 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 146,
      "r": 17
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 3 裡有幾個 21：取 0",
        "expr": "floor(3/21)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×21=0，3−0=3",
        "expr": "3-0*21",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "把下一位 0 拉下來，變成 30。"
      },
      {
        "k": "compute",
        "say": "看 30 裡有幾個 21：取 1",
        "expr": "floor(30/21)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×21=21，30−21=9",
        "expr": "30-1*21",
        "value": "9"
      },
      {
        "k": "compute",
        "say": "把下一位 8 拉下來，變成 98。"
      },
      {
        "k": "compute",
        "say": "看 98 裡有幾個 21：取 4",
        "expr": "floor(98/21)",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "4×21=84，98−84=14",
        "expr": "98-4*21",
        "value": "14"
      },
      {
        "k": "compute",
        "say": "把下一位 3 拉下來，變成 143。"
      },
      {
        "k": "compute",
        "say": "看 143 裡有幾個 21：取 6",
        "expr": "floor(143/21)",
        "value": "6"
      },
      {
        "k": "compute",
        "say": "6×21=126，143−126=17",
        "expr": "143-6*21",
        "value": "17"
      },
      {
        "k": "result",
        "say": "所以商是 146，餘數是 17。",
        "value": "146"
      },
      {
        "k": "check",
        "say": "驗算：21×146+17=3083（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.090Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-007",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 4577,
      "divisor": 36
    },
    "prompt": "4577 ÷ 36 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 127,
      "r": 5
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 4 裡有幾個 36：取 0",
        "expr": "floor(4/36)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×36=0，4−0=4",
        "expr": "4-0*36",
        "value": "4"
      },
      {
        "k": "compute",
        "say": "把下一位 5 拉下來，變成 45。"
      },
      {
        "k": "compute",
        "say": "看 45 裡有幾個 36：取 1",
        "expr": "floor(45/36)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×36=36，45−36=9",
        "expr": "45-1*36",
        "value": "9"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 97。"
      },
      {
        "k": "compute",
        "say": "看 97 裡有幾個 36：取 2",
        "expr": "floor(97/36)",
        "value": "2"
      },
      {
        "k": "compute",
        "say": "2×36=72，97−72=25",
        "expr": "97-2*36",
        "value": "25"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 257。"
      },
      {
        "k": "compute",
        "say": "看 257 裡有幾個 36：取 7",
        "expr": "floor(257/36)",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "7×36=252，257−252=5",
        "expr": "257-7*36",
        "value": "5"
      },
      {
        "k": "result",
        "say": "所以商是 127，餘數是 5。",
        "value": "127"
      },
      {
        "k": "check",
        "say": "驗算：36×127+5=4577（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.091Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-008",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 5097,
      "divisor": 27
    },
    "prompt": "5097 ÷ 27 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 188,
      "r": 21
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 5 裡有幾個 27：取 0",
        "expr": "floor(5/27)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×27=0，5−0=5",
        "expr": "5-0*27",
        "value": "5"
      },
      {
        "k": "compute",
        "say": "把下一位 0 拉下來，變成 50。"
      },
      {
        "k": "compute",
        "say": "看 50 裡有幾個 27：取 1",
        "expr": "floor(50/27)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×27=27，50−27=23",
        "expr": "50-1*27",
        "value": "23"
      },
      {
        "k": "compute",
        "say": "把下一位 9 拉下來，變成 239。"
      },
      {
        "k": "compute",
        "say": "看 239 裡有幾個 27：取 8",
        "expr": "floor(239/27)",
        "value": "8"
      },
      {
        "k": "compute",
        "say": "8×27=216，239−216=23",
        "expr": "239-8*27",
        "value": "23"
      },
      {
        "k": "compute",
        "say": "把下一位 7 拉下來，變成 237。"
      },
      {
        "k": "compute",
        "say": "看 237 裡有幾個 27：取 8",
        "expr": "floor(237/27)",
        "value": "8"
      },
      {
        "k": "compute",
        "say": "8×27=216，237−216=21",
        "expr": "237-8*27",
        "value": "21"
      },
      {
        "k": "result",
        "say": "所以商是 188，餘數是 21。",
        "value": "188"
      },
      {
        "k": "check",
        "say": "驗算：27×188+21=5097（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.091Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-009",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 7241,
      "divisor": 33
    },
    "prompt": "7241 ÷ 33 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 219,
      "r": 14
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 7 裡有幾個 33：取 0",
        "expr": "floor(7/33)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×33=0，7−0=7",
        "expr": "7-0*33",
        "value": "7"
      },
      {
        "k": "compute",
        "say": "把下一位 2 拉下來，變成 72。"
      },
      {
        "k": "compute",
        "say": "看 72 裡有幾個 33：取 2",
        "expr": "floor(72/33)",
        "value": "2"
      },
      {
        "k": "compute",
        "say": "2×33=66，72−66=6",
        "expr": "72-2*33",
        "value": "6"
      },
      {
        "k": "compute",
        "say": "把下一位 4 拉下來，變成 64。"
      },
      {
        "k": "compute",
        "say": "看 64 裡有幾個 33：取 1",
        "expr": "floor(64/33)",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "1×33=33，64−33=31",
        "expr": "64-1*33",
        "value": "31"
      },
      {
        "k": "compute",
        "say": "把下一位 1 拉下來，變成 311。"
      },
      {
        "k": "compute",
        "say": "看 311 裡有幾個 33：取 9",
        "expr": "floor(311/33)",
        "value": "9"
      },
      {
        "k": "compute",
        "say": "9×33=297，311−297=14",
        "expr": "311-9*33",
        "value": "14"
      },
      {
        "k": "result",
        "say": "所以商是 219，餘數是 14。",
        "value": "219"
      },
      {
        "k": "check",
        "say": "驗算：33×219+14=7241（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.091Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_div-010",
    "grade": 5,
    "topic": "word_problem_div_with_remainder",
    "type": "div_with_remainder",
    "params": {
      "dividend": 16350,
      "divisor": 42
    },
    "prompt": "16350 ÷ 42 = ?（寫出商和餘數，並驗算）",
    "answer": {
      "q": 389,
      "r": 12
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "用長除法：每次看前面能除幾次，寫商、相減、再把下一位拉下來。"
      },
      {
        "k": "formula",
        "say": "最後要驗算：除數×商 + 餘數 = 被除數。"
      },
      {
        "k": "compute",
        "say": "看 1 裡有幾個 42：取 0",
        "expr": "floor(1/42)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×42=0，1−0=1",
        "expr": "1-0*42",
        "value": "1"
      },
      {
        "k": "compute",
        "say": "把下一位 6 拉下來，變成 16。"
      },
      {
        "k": "compute",
        "say": "看 16 裡有幾個 42：取 0",
        "expr": "floor(16/42)",
        "value": "0"
      },
      {
        "k": "compute",
        "say": "0×42=0，16−0=16",
        "expr": "16-0*42",
        "value": "16"
      },
      {
        "k": "compute",
        "say": "把下一位 3 拉下來，變成 163。"
      },
      {
        "k": "compute",
        "say": "看 163 裡有幾個 42：取 3",
        "expr": "floor(163/42)",
        "value": "3"
      },
      {
        "k": "compute",
        "say": "3×42=126，163−126=37",
        "expr": "163-3*42",
        "value": "37"
      },
      {
        "k": "compute",
        "say": "把下一位 5 拉下來，變成 375。"
      },
      {
        "k": "compute",
        "say": "看 375 裡有幾個 42：取 8",
        "expr": "floor(375/42)",
        "value": "8"
      },
      {
        "k": "compute",
        "say": "8×42=336，375−336=39",
        "expr": "375-8*42",
        "value": "39"
      },
      {
        "k": "compute",
        "say": "把下一位 0 拉下來，變成 390。"
      },
      {
        "k": "compute",
        "say": "看 390 裡有幾個 42：取 9",
        "expr": "floor(390/42)",
        "value": "9"
      },
      {
        "k": "compute",
        "say": "9×42=378，390−378=12",
        "expr": "390-9*42",
        "value": "12"
      },
      {
        "k": "result",
        "say": "所以商是 389，餘數是 12。",
        "value": "389"
      },
      {
        "k": "check",
        "say": "驗算：42×389+12=16350（要相等才對）。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.091Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-001",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 161,
      "a": 918,
      "b": 347
    },
    "prompt": "161×918 − 161×347 = ?",
    "answer": {
      "ans": 91931
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 161，先改寫成：161×(918−347)。"
      },
      {
        "k": "compute",
        "say": "先算括號：918−347=571",
        "expr": "918-347",
        "value": "571"
      },
      {
        "k": "compute",
        "say": "再乘回去：161×571=91931",
        "expr": "161*571",
        "value": "91931"
      },
      {
        "k": "result",
        "say": "所以答案是 91931。",
        "value": "91931"
      },
      {
        "k": "check",
        "say": "檢查：把 161×918 和 161×347 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.092Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-002",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 394,
      "a": 469,
      "b": 410
    },
    "prompt": "394×469 − 394×410 = ?",
    "answer": {
      "ans": 23246
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 394，先改寫成：394×(469−410)。"
      },
      {
        "k": "compute",
        "say": "先算括號：469−410=59",
        "expr": "469-410",
        "value": "59"
      },
      {
        "k": "compute",
        "say": "再乘回去：394×59=23246",
        "expr": "394*59",
        "value": "23246"
      },
      {
        "k": "result",
        "say": "所以答案是 23246。",
        "value": "23246"
      },
      {
        "k": "check",
        "say": "檢查：把 394×469 和 394×410 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.092Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-003",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 210,
      "a": 253,
      "b": 173
    },
    "prompt": "210×253 − 210×173 = ?",
    "answer": {
      "ans": 16800
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 210，先改寫成：210×(253−173)。"
      },
      {
        "k": "compute",
        "say": "先算括號：253−173=80",
        "expr": "253-173",
        "value": "80"
      },
      {
        "k": "compute",
        "say": "再乘回去：210×80=16800",
        "expr": "210*80",
        "value": "16800"
      },
      {
        "k": "result",
        "say": "所以答案是 16800。",
        "value": "16800"
      },
      {
        "k": "check",
        "say": "檢查：把 210×253 和 210×173 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.092Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-004",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 251,
      "a": 359,
      "b": 335
    },
    "prompt": "251×359 − 251×335 = ?",
    "answer": {
      "ans": 6024
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 251，先改寫成：251×(359−335)。"
      },
      {
        "k": "compute",
        "say": "先算括號：359−335=24",
        "expr": "359-335",
        "value": "24"
      },
      {
        "k": "compute",
        "say": "再乘回去：251×24=6024",
        "expr": "251*24",
        "value": "6024"
      },
      {
        "k": "result",
        "say": "所以答案是 6024。",
        "value": "6024"
      },
      {
        "k": "check",
        "say": "檢查：把 251×359 和 251×335 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.092Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-005",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 391,
      "a": 650,
      "b": 43
    },
    "prompt": "391×650 − 391×43 = ?",
    "answer": {
      "ans": 237337
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 391，先改寫成：391×(650−43)。"
      },
      {
        "k": "compute",
        "say": "先算括號：650−43=607",
        "expr": "650-43",
        "value": "607"
      },
      {
        "k": "compute",
        "say": "再乘回去：391×607=237337",
        "expr": "391*607",
        "value": "237337"
      },
      {
        "k": "result",
        "say": "所以答案是 237337。",
        "value": "237337"
      },
      {
        "k": "check",
        "say": "檢查：把 391×650 和 391×43 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.092Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-006",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 191,
      "a": 581,
      "b": 130
    },
    "prompt": "191×581 − 191×130 = ?",
    "answer": {
      "ans": 86141
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 191，先改寫成：191×(581−130)。"
      },
      {
        "k": "compute",
        "say": "先算括號：581−130=451",
        "expr": "581-130",
        "value": "451"
      },
      {
        "k": "compute",
        "say": "再乘回去：191×451=86141",
        "expr": "191*451",
        "value": "86141"
      },
      {
        "k": "result",
        "say": "所以答案是 86141。",
        "value": "86141"
      },
      {
        "k": "check",
        "say": "檢查：把 191×581 和 191×130 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.093Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-007",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 179,
      "a": 755,
      "b": 301
    },
    "prompt": "179×755 − 179×301 = ?",
    "answer": {
      "ans": 81266
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 179，先改寫成：179×(755−301)。"
      },
      {
        "k": "compute",
        "say": "先算括號：755−301=454",
        "expr": "755-301",
        "value": "454"
      },
      {
        "k": "compute",
        "say": "再乘回去：179×454=81266",
        "expr": "179*454",
        "value": "81266"
      },
      {
        "k": "result",
        "say": "所以答案是 81266。",
        "value": "81266"
      },
      {
        "k": "check",
        "say": "檢查：把 179×755 和 179×301 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.093Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-008",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 320,
      "a": 573,
      "b": 82
    },
    "prompt": "320×573 − 320×82 = ?",
    "answer": {
      "ans": 157120
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 320，先改寫成：320×(573−82)。"
      },
      {
        "k": "compute",
        "say": "先算括號：573−82=491",
        "expr": "573-82",
        "value": "491"
      },
      {
        "k": "compute",
        "say": "再乘回去：320×491=157120",
        "expr": "320*491",
        "value": "157120"
      },
      {
        "k": "result",
        "say": "所以答案是 157120。",
        "value": "157120"
      },
      {
        "k": "check",
        "say": "檢查：把 320×573 和 320×82 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.093Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-009",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 320,
      "a": 884,
      "b": 615
    },
    "prompt": "320×884 − 320×615 = ?",
    "answer": {
      "ans": 86080
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 320，先改寫成：320×(884−615)。"
      },
      {
        "k": "compute",
        "say": "先算括號：884−615=269",
        "expr": "884-615",
        "value": "269"
      },
      {
        "k": "compute",
        "say": "再乘回去：320×269=86080",
        "expr": "320*269",
        "value": "86080"
      },
      {
        "k": "result",
        "say": "所以答案是 86080。",
        "value": "86080"
      },
      {
        "k": "check",
        "say": "檢查：把 320×884 和 320×615 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.093Z",
      "generator": "tools/gold_bank_generate.js"
    }
  },
  {
    "id": "offline_dist-010",
    "grade": 5,
    "topic": "arithmetic_distributive",
    "type": "arithmetic_distributive_sub",
    "params": {
      "k": 388,
      "a": 509,
      "b": 20
    },
    "prompt": "388×509 − 388×20 = ?",
    "answer": {
      "ans": 189732
    },
    "teacherSteps": [
      {
        "k": "concept",
        "say": "先找出兩項都有的相同因數（公因數），用分配律可以算得更快。"
      },
      {
        "k": "formula",
        "say": "k×a − k×b = k×(a−b)。"
      },
      {
        "k": "compute",
        "say": "這題公因數是 388，先改寫成：388×(509−20)。"
      },
      {
        "k": "compute",
        "say": "先算括號：509−20=489",
        "expr": "509-20",
        "value": "489"
      },
      {
        "k": "compute",
        "say": "再乘回去：388×489=189732",
        "expr": "388*489",
        "value": "189732"
      },
      {
        "k": "result",
        "say": "所以答案是 189732。",
        "value": "189732"
      },
      {
        "k": "check",
        "say": "檢查：把 388×509 和 388×20 分別算出來再相減，結果要一樣。"
      }
    ],
    "source": {
      "pdf": "104五上期末數學.pdf/108-1期末評量答案卷：5年級數學.pdf",
      "page": null,
      "qno": null
    },
    "meta": {
      "generatedAt": "2026-01-18T07:33:12.093Z",
      "generator": "tools/gold_bank_generate.js"
    }
  }
];
