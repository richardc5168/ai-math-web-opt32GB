#!/usr/bin/env node
'use strict';
var fs = require('fs');
var path = require('path');

var DOCS = path.join(__dirname, '..', 'docs', 'volume-g5', 'bank.js');
var DIST = path.join(__dirname, '..', 'dist_ai_math_web_pages', 'docs', 'volume-g5', 'bank.js');

var src = fs.readFileSync(DOCS, 'utf8');
var w = {};
new Function('window', src)(w);
var bank = w.VOLUME_G5_BANK;
console.log('Before:', bank.length);
if (bank.length !== 200) { console.error('Expected 200'); process.exit(1); }

var T = '國小五年級｜體積（長方體/正方體）';
var cm1 = ['長寬高算錯。', '忘了乘以高。'];
var maxN = {};
bank.forEach(function(q) {
  var m = q.id.match(/(\d+)$/);
  if (m) { var n = parseInt(m[1]); if (!maxN[q.kind] || n > maxN[q.kind]) maxN[q.kind] = n; }
});

function nextId(prefix, kind) {
  if (!maxN[kind]) maxN[kind] = 0;
  maxN[kind]++;
  var s = String(maxN[kind]);
  while (s.length < 3) s = '0' + s;
  return prefix + '_' + s;
}

// ===== rect_cm3 +5 =====
[[25,14,9],[18,22,7],[31,6,15],[12,19,13],[27,8,11]].forEach(function(d) {
  var l=d[0],wi=d[1],h=d[2],v=l*wi*h;
  bank.push({id:nextId('vg5_rect','rect_cm3'),kind:'rect_cm3',topic:T,difficulty:'easy',
    question:'（長方體體積）長 '+l+' 公分、寬 '+wi+' 公分、高 '+h+' 公分的長方體，體積是多少立方公分？',
    answer:String(v),
    hints:['⭐ 觀念提醒\n長方體體積 = 長 × 寬 × 高。',
      '📊 '+l+' × '+wi+' = '+(l*wi)+'。',
      '📐 一步步算：\n① 長×寬 = '+l+'×'+wi+' = '+(l*wi)+'\n② 再×高 = '+(l*wi)+'×'+h+'\n③ 得出體積\n④ 加單位\n算完記得回頭檢查喔！✅',
      '👉 長×寬×高就是體積。'],
    steps:[l+'×'+wi+'='+(l*wi),(l*wi)+'×'+h+'='+v,'體積 = '+v+' cm³'],
    meta:{unit:'立方公分（cm³）'},
    explanation:'長×寬×高 = '+l+'×'+wi+'×'+h+' = '+v+' cm³。',
    common_mistakes:cm1});
});

// ===== base_area_h +10 =====
[[135,9],[148,7],[162,6],[88,14],[210,5],[176,8],[95,12],[124,11],[156,13],[200,4]].forEach(function(d) {
  var area=d[0],h=d[1],v=area*h;
  bank.push({id:nextId('vg5_base','base_area_h'),kind:'base_area_h',topic:T,difficulty:'easy',
    question:'（底面積×高）一個立體的底面積是 '+area+' 平方公分，高是 '+h+' 公分，體積是多少立方公分？',
    answer:String(v),
    hints:['⭐ 觀念提醒\n體積 = 底面積 × 高。',
      '📊 '+area+' × '+h+' = '+v+'。',
      '📐 一步步算：\n① 底面積 = '+area+'\n② 高 = '+h+'\n③ 底面積 × 高\n④ 得出體積\n算完記得回頭檢查喔！✅',
      '👉 底面積×高就是體積，別忘了單位。'],
    steps:['底面積 = '+area+' cm²','高 = '+h+' cm',area+'×'+h+' = '+v,'體積 = '+v+' cm³'],
    meta:{unit:'立方公分（cm³）'},
    explanation:'底面積×高 = '+area+'×'+h+' = '+v+' cm³。',
    common_mistakes:cm1});
});

// ===== composite +10 (two rectangular prisms) =====
[[14,6,8,14,4,8],[16,5,10,16,3,10],[20,7,6,20,5,6],[11,9,12,11,4,12],[18,8,5,18,6,5],
 [15,10,7,15,3,7],[22,4,9,22,6,9],[13,7,11,13,5,11],[17,8,6,17,4,6],[19,5,8,19,7,8]].forEach(function(d) {
  var al=d[0],aw=d[1],ah=d[2],bl=d[3],bw=d[4],bh=d[5];
  var va=al*aw*ah, vb=bl*bw*bh, tot=va+vb;
  bank.push({id:nextId('vg5_comp','composite'),kind:'composite',topic:T,difficulty:'medium',
    question:'（複合形體）把形體分成兩個長方體來算：\nA：長 '+al+' 公分、寬 '+aw+' 公分、高 '+ah+' 公分\nB：長 '+bl+' 公分、寬 '+bw+' 公分、高 '+bh+' 公分\n這個複合形體的總體積是多少立方公分？',
    answer:String(tot),
    hints:['⭐ 觀念提醒\n複合形體：分成兩個長方體分別算再相加。',
      '📊 A = '+al+'×'+aw+'×'+ah+' = '+va+'。',
      '📐 一步步算：\n① V_A = '+al+'×'+aw+'×'+ah+' = '+va+'\n② V_B = '+bl+'×'+bw+'×'+bh+' = '+vb+'\n③ 合計 = '+va+'+'+vb+'\n④ 確認\n算完記得回頭檢查喔！✅',
      '👉 分別計算再加總。'],
    steps:['V_A = '+al+'×'+aw+'×'+ah+' = '+va,'V_B = '+bl+'×'+bw+'×'+bh+' = '+vb,'總體積 = '+va+'+'+vb+' = '+tot],
    meta:{unit:'立方公分（cm³）'},
    explanation:'V_A = '+va+', V_B = '+vb+', 總體積 = '+tot+' cm³。',
    common_mistakes:cm1});
});

// ===== cube_cm3 +10 =====
[11,13,14,16,17,19,21,23,24,26].forEach(function(s) {
  var v=s*s*s;
  bank.push({id:nextId('vg5_cube','cube_cm3'),kind:'cube_cm3',topic:T,difficulty:'easy',
    question:'（正方體體積）邊長 '+s+' 公分的正方體，體積是多少立方公分？',
    answer:String(v),
    hints:['⭐ 觀念提醒\n正方體體積 = 邊長³。',
      '📊 '+s+'×'+s+' = '+(s*s)+'。',
      '📐 一步步算：\n① 先算 '+s+'×'+s+' = '+(s*s)+'\n② 再乘以 '+s+'\n③ 得出體積\n④ 加單位\n算完記得回頭檢查喔！✅',
      '👉 邊長×邊長×邊長就是正方體體積。'],
    steps:[s+'²='+(s*s),(s*s)+'×'+s+'='+v,'體積 = '+v+' cm³'],
    meta:{unit:'立方公分（cm³）'},
    explanation:s+'³ = '+v+' cm³。',
    common_mistakes:cm1});
});

// ===== mixed_units +10 =====
// length has m, width/height in cm
[[2,60,20],[1,80,25],[3,40,10],[2,50,30],[1,90,15],[2,70,12],[3,30,20],[1,40,35],[2,80,18],[3,50,14]].forEach(function(d) {
  var lm=d[0],wcm=d[1],hcm=d[2];
  var lcm=lm*100, v=lcm*wcm*hcm;
  bank.push({id:nextId('vg5_mixed','mixed_units'),kind:'mixed_units',topic:T,difficulty:'medium',
    question:'（單位混合）一個長方體的長是 '+lm+' 公尺、寬是 '+wcm+' 公分、高是 '+hcm+' 公分。體積是多少立方公分（cm³）？',
    answer:String(v),
    hints:['⭐ 觀念提醒\n先統一單位（公尺→公分：×100），再算體積。',
      '📊 '+lm+' 公尺 = '+lcm+' 公分。',
      '📐 一步步算：\n① '+lm+' 公尺 = '+lcm+' 公分\n② '+lcm+'×'+wcm+'×'+hcm+'\n③ 計算體積\n④ 確認\n算完記得回頭檢查喔！✅',
      '👉 先換算單位再計算。'],
    steps:[lm+' m = '+lcm+' cm',lcm+'×'+wcm+'='+(lcm*wcm),(lcm*wcm)+'×'+hcm+'='+v,'體積 = '+v+' cm³'],
    meta:{unit:'立方公分（cm³）'},
    explanation:lm+' 公尺 = '+lcm+' cm，'+lcm+'×'+wcm+'×'+hcm+' = '+v+' cm³。',
    common_mistakes:['忘了換算單位。','公尺換公分少乘100。']});
});

// ===== decimal_dims +10 =====
// Use integer arithmetic: multiply all dims by 10, compute, then format
[[15,12,8],[22,15,6],[18,14,5],[25,8,3],[32,15,3],[14,12,10],[24,5,8],[16,25,3],[28,5,6],[35,4,2]].forEach(function(d) {
  // dims in tenths of m: 15 = 1.5 m, etc.
  var a=d[0],b=d[1],c=d[2];
  var prod = a*b*c; // in thousandths of m³
  // format: prod/1000, remove trailing zeros
  var intPart = Math.floor(prod/1000);
  var fracPart = prod % 1000;
  var ans;
  if (fracPart === 0) { ans = String(intPart); }
  else {
    var s = String(fracPart);
    while (s.length < 3) s = '0' + s;
    while (s.charAt(s.length-1) === '0') s = s.substring(0, s.length-1);
    ans = intPart + '.' + s;
  }
  var lStr = (a/10).toString(), wStr = (b/10).toString(), hStr = (c/10).toString();
  bank.push({id:nextId('vg5_dec','decimal_dims'),kind:'decimal_dims',topic:T,difficulty:'medium',
    question:'（帶小數尺寸）一個長方體的長 '+lStr+' 公尺、寬 '+wStr+' 公尺、高 '+hStr+' 公尺。體積是多少立方公尺（m³）？（可填小數）',
    answer:ans,
    hints:['⭐ 觀念提醒\n帶小數的長方體，直接長×寬×高。',
      '📊 '+lStr+' × '+wStr+' = '+(a*b/100)+'。',
      '📐 一步步算：\n① 長×寬 = '+lStr+'×'+wStr+'\n② 再×高 = ×'+hStr+'\n③ 得出體積\n④ 確認\n算完記得回頭檢查喔！✅',
      '👉 小數乘法要注意小數點位置。'],
    steps:[lStr+'×'+wStr+'='+(a*b/100),(a*b/100)+'×'+hStr+'='+ans,'體積 = '+ans+' m³'],
    meta:{unit:'立方公尺（m³）'},
    explanation:lStr+'×'+wStr+'×'+hStr+' = '+ans+' m³。',
    common_mistakes:['小數乘法算錯。','小數點位數錯誤。']});
});

// ===== composite3 +10 =====
[[10,8,6,10,4,6,10,5,6],[12,7,5,12,3,5,12,6,5],[15,6,4,15,4,4,15,3,4],[8,10,7,8,5,7,8,3,7],
 [14,5,8,14,3,8,14,7,8],[9,8,10,9,4,10,9,6,10],[11,7,9,11,3,9,11,5,9],[16,4,6,16,6,6,16,3,6],
 [13,5,7,13,8,7,13,4,7],[20,3,5,20,6,5,20,4,5]].forEach(function(d) {
  var al=d[0],aw=d[1],ah=d[2],bl=d[3],bw=d[4],bh=d[5],cl=d[6],cw=d[7],ch=d[8];
  var va=al*aw*ah,vb=bl*bw*bh,vc=cl*cw*ch,tot=va+vb+vc;
  bank.push({id:nextId('vg5_comp3','composite3'),kind:'composite3',topic:T,difficulty:'hard',
    question:'（複合形體進階｜三段相加）把形體分成三個長方體來算：\nA：長 '+al+' 公分、寬 '+aw+' 公分、高 '+ah+' 公分\nB：長 '+bl+' 公分、寬 '+bw+' 公分、高 '+bh+' 公分\nC：長 '+cl+' 公分、寬 '+cw+' 公分、高 '+ch+' 公分\n這個複合形體的總體積是多少立方公分？',
    answer:String(tot),
    hints:['⭐ 觀念提醒\n分成三個長方體分別算再加總。',
      '📊 V_A = '+al+'×'+aw+'×'+ah+' = '+va+'。',
      '📐 一步步算：\n① V_A = '+va+'\n② V_B = '+vb+'\n③ V_C = '+vc+'\n④ 合計\n算完記得回頭檢查喔！✅',
      '👉 三個體積分別算，最後相加。'],
    steps:['分解成 A('+al+'×'+aw+'×'+ah+')、B('+bl+'×'+bw+'×'+bh+')、C('+cl+'×'+cw+'×'+ch+')','V_A='+va+', V_B='+vb+', V_C='+vc,'總體積 = '+va+'+'+vb+'+'+vc+' = '+tot],
    meta:{unit:'立方公分（cm³）'},
    explanation:'V_A='+va+', V_B='+vb+', V_C='+vc+', 合計='+tot+' cm³。',
    common_mistakes:['其中一個體積算錯。','忘了加第三段。']});
});

// ===== rect_find_height +10 =====
[[30,6,1260],[24,8,1152],[15,13,1755],[20,9,1440],[28,5,980],[18,7,1134],[22,11,1694],[16,14,2688],[25,4,900],[32,3,864]].forEach(function(d) {
  var l=d[0],wi=d[1],v=d[2],h=v/(l*wi);
  bank.push({id:nextId('vg5_rect_find_h','rect_find_height'),kind:'rect_find_height',topic:T,difficulty:'medium',
    question:'（反求高）一個長方體的長是 '+l+' 公分、寬是 '+wi+' 公分，體積是 '+v+' 立方公分（cm³）。它的高是多少公分？（請填整數）',
    answer:String(h),
    hints:['⭐ 觀念提醒\n高 = 體積 ÷ (長 × 寬)。',
      '📊 底面積 = '+l+' × '+wi+' = '+(l*wi)+'。',
      '📐 一步步算：\n① 底面積 = '+l+'×'+wi+' = '+(l*wi)+'\n② 高 = '+v+' ÷ '+(l*wi)+'\n③ 計算結果\n④ 驗算\n算完記得回頭檢查喔！✅',
      '👉 體積÷底面積就是高。'],
    steps:['底面積 = '+l+'×'+wi+' = '+(l*wi),'高 = '+v+'÷'+(l*wi)+' = '+h,'驗算: '+(l*wi)+'×'+h+' = '+v+' ✓'],
    meta:{unit:'公分（cm）'},
    explanation:'高 = '+v+' ÷ '+(l*wi)+' = '+h+' cm。',
    common_mistakes:['除法算錯。','忘了先算底面積。']});
});

// ===== cube_find_edge +10 =====
[8,27,64,125,216,343,512,729,1728,1331].forEach(function(v) {
  var s = Math.round(Math.pow(v, 1/3));
  bank.push({id:nextId('vg5_cube_find','cube_find_edge'),kind:'cube_find_edge',topic:T,difficulty:'medium',
    question:'（反求邊長）一個正方體的體積是 '+v+' 立方公分（cm³），它的邊長是多少公分？（請填整數）',
    answer:String(s),
    hints:['⭐ 觀念提醒\n邊長 = ∛體積。',
      '📊 試試看哪個數的三次方 = '+v+'。',
      '📐 一步步算：\n① 找一個數 n，使得 n×n×n = '+v+'\n② 從小的數開始試算\n③ 驗證 n³ 是否正確\n④ 得出邊長\n算完記得回頭檢查喔！✅',
      '👉 找出三次方等於體積的數。'],
    steps:['∛'+v+' = ?',s+'×'+s+'='+(s*s),(s*s)+'×'+s+'='+v,'邊長 = '+s+' cm'],
    meta:{unit:'公分（cm）'},
    explanation:'∛'+v+' = '+s+' cm。',
    common_mistakes:['立方根算錯。','和平方根搞混。']});
});

// ===== cm3_to_m3 +8 =====
[3,5,7,8,11,12,15,18].forEach(function(m3) {
  var cm3 = m3 * 1000000;
  var cm3Str = cm3.toLocaleString('en-US');
  bank.push({id:nextId('vg5_cm3_to_m3','cm3_to_m3'),kind:'cm3_to_m3',topic:T,difficulty:'easy',
    question:'（單位換算）'+cm3Str+' 立方公分（cm³）等於多少立方公尺（m³）？（請填整數）',
    answer:String(m3),
    hints:['⭐ 觀念提醒\n1 m³ = 1,000,000 cm³。',
      '📊 '+cm3Str+' ÷ 1,000,000 = '+m3+'。',
      '📐 一步步算：\n① 記住 1 m³ = 1,000,000 cm³\n② 把 cm³ 數字除以 1,000,000\n③ 算出有幾個百萬\n④ 確認\n算完記得回頭檢查喔！✅',
      '👉 cm³ → m³ 除以 1,000,000。'],
    steps:['1 m³ = 1,000,000 cm³',cm3Str+' ÷ 1,000,000 = '+m3,'= '+m3+' m³'],
    meta:{unit:'立方公尺（m³）'},
    explanation:cm3Str+' cm³ = '+m3+' m³。',
    common_mistakes:['忘了除以 1,000,000。','少算零的個數。']});
});

// ===== m3_to_cm3 +7 =====
[2,3,5,7,8,10,12].forEach(function(m3) {
  var cm3 = m3 * 1000000;
  var cm3Str = cm3.toLocaleString('en-US');
  bank.push({id:nextId('vg5_m3_to_cm3','m3_to_cm3'),kind:'m3_to_cm3',topic:T,difficulty:'easy',
    question:'（單位換算）'+m3+' 立方公尺（m³）等於多少立方公分（cm³）？',
    answer:String(cm3),
    hints:['⭐ 觀念提醒\n1 m³ = 1,000,000 cm³。',
      '📊 '+m3+' × 1,000,000 = '+cm3Str+'。',
      '📐 一步步算：\n① 記住 1 m³ = 1,000,000 cm³\n② 把 m³ 數字乘以 1,000,000\n③ 加上六個零\n④ 確認\n算完記得回頭檢查喔！✅',
      '👉 m³ → cm³ 乘以 1,000,000。'],
    steps:['1 m³ = 1,000,000 cm³',m3+' × 1,000,000 = '+cm3Str,'= '+cm3Str+' cm³'],
    meta:{unit:'立方公分（cm³）'},
    explanation:m3+' m³ = '+cm3Str+' cm³。',
    common_mistakes:['忘了乘以 1,000,000。','零的個數算錯。']});
});

// ---- Verify ----
console.log('After:', bank.length);
if (bank.length !== 300) { console.error('EXPECTED 300, got', bank.length); process.exit(1); }
var ids = {};
for (var qi = 0; qi < bank.length; qi++) {
  if (ids[bank[qi].id]) { console.error('DUPLICATE ID:', bank[qi].id); process.exit(1); }
  ids[bank[qi].id] = true;
}
for (var ni = 200; ni < 300; ni++) {
  var q = bank[ni];
  if (!q.answer || q.answer === 'undefined') { console.error('BAD ANSWER:', q.id); process.exit(1); }
  if (q.hints[2].indexOf(q.answer) !== -1 && q.answer.length > 1) {
    console.error('L3 HINT LEAK:', q.id, 'answer=' + q.answer); process.exit(1);
  }
}
console.log('All 100 new questions verified.');

var out = '/* eslint-disable */\nwindow.VOLUME_G5_BANK = ' + JSON.stringify(bank, null, 2) + ';\n';
fs.writeFileSync(DOCS, out, 'utf8');
fs.writeFileSync(DIST, out, 'utf8');
console.log('Done. 200 → 300. Written to docs/ and dist/.');
