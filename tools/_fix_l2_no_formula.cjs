#!/usr/bin/env node
// Fix L2_NO_FORMULA violations by adding formula/列式 keywords to L2 hints
// Run: node tools/_fix_l2_no_formula.cjs
"use strict";
var fs = require("fs");
var path = require("path");

// Fixes: map question_id → new L2 hint text
var FIXES = {
  // g5-grand-slam
  "g5gs_line_omit_11": "列式：省略符號「…」表示中間省略，做法：直接想省略符號的定義。",
  "g5gs_vol_cm3ml_12": "列式：1 cm³ = 1 mL，做法：直接看數字即可。",
  // offline-math
  "offline_dist-029": "列式：追趕時間 = 距離差 ÷ 速度差。先算速度差。",
  "offline_dist-034": "列式：平均速度 = 總距離 ÷ 總時間。不能直接平均速度！",
  "offline_dec-026": "列式：豎式加法，從最低位開始加，進位。",
  "offline_dec-027": "列式：豎式減法，不夠減要借位。",
  "offline_dec-033": "列式：四捨五入規則 — 第二位是4，<5捨去。",
  "offline_dec-034": "列式：豎式加法，從最低位加起。",
  "offline_time-032": "列式：時間減法，分不夠減要借 1 時 = 60 分。20分不夠減45分。",
  // ratio-percent-g5
  "rp5_pct_mean_12": "列式：百分數 = 部分 ÷ 全部 × 100%。% 前面的數字就是每 100 份中所佔的份數。",
  "rp5_pct_mean_13": "列式：百分數 = 部分 ÷ 全部 × 100%。% 前面的數字就是每 100 份中所佔的份數。",
  "rp5_pct_mean_14": "列式：百分數 = 部分 ÷ 全部 × 100%。% 前面的數字就是每 100 份中所佔的份數。",
  "rp5_pct_mean_15": "列式：百分數 = 部分 ÷ 全部 × 100%。% 前面的數字就是每 100 份中所佔的份數。",
  // volume-g5
  "vg5_cube_find_09": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 64？",
  "vg5_cube_find_10": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 216？",
  "vg5_cube_find_11": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 729？",
  "vg5_cube_find_12": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 1331？",
  "vg5_cube_find_13": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 1728？",
  "vg5_cube_find_14": "列式：邊長³ = 體積，所以邊長 = ³√體積。試試看哪個整數連乘三次等於 3375？"
};

var MODULE_BANKS = {
  "g5-grand-slam": { src: "docs/g5-grand-slam/bank.js", varPat: /window\.G5_GRAND_SLAM_BANK/ },
  "offline-math": { src: "docs/offline-math/bank.js", varPat: /window\.OFFLINE_MATH_BANK/ },
  "ratio-percent-g5": { src: "docs/ratio-percent-g5/bank.js", varPat: /window\.RATIO_PERCENT_G5_BANK/ },
  "volume-g5": { src: "docs/volume-g5/bank.js", varPat: /window\.VOLUME_G5_BANK/ }
};

var totalFixed = 0;

Object.keys(MODULE_BANKS).forEach(function(mod) {
  var info = MODULE_BANKS[mod];
  var srcPath = path.join(__dirname, "..", info.src);
  var distPath = path.join(__dirname, "..", "dist_ai_math_web_pages", info.src);

  var src = fs.readFileSync(srcPath, "utf8");
  var match = src.match(/^([\s\S]*?(?:window\.\w+)\s*=\s*)([\s\S]+?)(;\s*$)/m);
  if (!match) { console.log("SKIP:", mod); return; }

  var bankArr;
  try { bankArr = (new Function("return " + match[2]))(); }
  catch(e) { console.log("SKIP eval:", mod); return; }

  var modFixed = 0;
  bankArr.forEach(function(q) {
    if (FIXES[q.id] && q.hints && q.hints.length >= 2) {
      q.hints[1] = FIXES[q.id];
      modFixed++;
    }
  });

  if (modFixed > 0) {
    var out = match[1] + JSON.stringify(bankArr, null, 2) + match[3];
    fs.writeFileSync(srcPath, out, "utf8");
    if (fs.existsSync(distPath)) fs.writeFileSync(distPath, out, "utf8");
    totalFixed += modFixed;
    console.log("Fixed", modFixed, "L2 hints in", mod);
  }
});

console.log("Total L2 fixes:", totalFixed);
