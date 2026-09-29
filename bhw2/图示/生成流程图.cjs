const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.env.BHW2_SHARP_PATH || 'sharp');

const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="810" viewBox="0 0 1100 810">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#526679"/></marker></defs>
<style>text{font-family:'Microsoft YaHei','SimHei',sans-serif;fill:#203349} .small{font-size:16px} .label{font-size:18px} .heading{font-size:21px;font-weight:600} .line{fill:none;stroke:#526679;stroke-width:1.7}</style>
<rect width="1100" height="810" fill="white"/>
<text x="40" y="35" class="heading">矩阵分块</text>
<text x="40" y="67" class="label">X 按列分为 8 块（输入位于 GPU 1）</text>
<text x="650" y="35" class="heading">W 按行分为 8 块</text>
<text x="845" y="105" class="small">权重提前分配</text>
<text x="845" y="134" class="small">每卡保留对应的 W 块</text>
<text x="40" y="215" class="small">X：128 × 8192</text>
<text x="650" y="215" class="small">W：8192 × 4096</text>`];
const colors = ['#e3eef9','#e6f3ed','#fff1d9','#eee8f7','#f8e6e7','#e0f1f1','#eeeedd','#e8ecf5'];
function rect(x,y,w,h,fill,stroke='#b8c5d1',radius=0) {
  parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}"/>`);
}
function text(x,y,value,size=17,anchor='start') {
  parts.push(`<text x="${x}" y="${y}" font-size="${size}" text-anchor="${anchor}">${value}</text>`);
}
function line(x1,y1,x2,y2,arrow=false) {
  parts.push(`<path d="M${x1},${y1} L${x2},${y2}" class="line"${arrow?' marker-end="url(#arrow)"':''}/>`);
}
for(let i=0;i<8;i++) {
  rect(40+i*60,85,60,103,colors[i]);
  text(70+i*60,142,`X${i+1}`,18,'middle');
  rect(650,51+i*18,165,18,colors[i]);
  text(732.5,65+i*18,`W${i+1}`,13,'middle');
}
line(40,237,1060,237);
text(40,272,'各卡的输入块与权重块',19);
text(452,272,'并行计算',19);
text(613,272,'部分结果',19);
for(let i=0;i<8;i++) {
  const y = 292 + i*55;
  rect(40,y,375,37,colors[i],'#b8c5d1',5);
  text(227.5,y+24,`X${i+1} (128×1024) × W${i+1} (1024×4096)`,16,'middle');
  line(417,y+18.5,441,y+18.5,true);
  rect(445,y,115,37,'#f5f7fa','#b8c5d1',5);
  text(502.5,y+25,`GPU ${i+1}`,18,'middle');
  line(563,y+18.5,596,y+18.5,true);
  rect(600,y,185,37,colors[i],'#b8c5d1',5);
  text(692.5,y+24,`P${i+1}：128×4096`,17,'middle');
  line(787,y+18.5,823,y+18.5);
}
line(823,310.5,823,695.5);
line(823,504,849,504,true);
rect(853,461,207,88,'#eaf0f7','#6988a4',7);
text(956.5,488,'GPU 1 逐元素求和',18,'middle');
text(956.5,518,'Y = P1 + ⋯ + P8',18,'middle');
text(956.5,402,'P1 留在本卡',16,'middle');
text(956.5,429,'P2 至 P8 传回 GPU 1',16,'middle');
line(956.5,552,956.5,586,true);
rect(853,591,207,69,'#f5f7fa','#6988a4',7);
text(956.5,618,'完整输出 Y',19,'middle');
text(956.5,644,'128 × 4096',18,'middle');
text(40,758,'GPU 1 分发 X2 至 X8；各卡完成局部乘法后，汇总部分结果。',18);
text(40,786,'每个 Pi 对应相同的输出位置，覆盖不同的输入特征，因此合并时相加。',18);
parts.push('</svg>');
const svg = parts.join('\n');
fs.writeFileSync(path.join(__dirname,'多GPU矩阵乘法流程.svg'),svg,'utf8');
sharp(Buffer.from(svg)).resize(2200,1620).png().toFile(path.join(__dirname,'多GPU矩阵乘法流程.png'))
  .then(()=>process.stdout.write('Diagram generated.\n')).catch(error=>{console.error(error);process.exitCode=1;});
