const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '..', 'battle', 'frontend');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
for (const script of html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(script[1]);
const score = vm.runInNewContext(fs.readFileSync(path.join(root, 'scoreboard.js'), 'utf8') + '\nBattleScore');
const old = [{id:'a',name:'A',rank:1,profit:100}, {id:'b',name:'B',rank:2,profit:0}];
const current = [{id:'b',name:'B',rank:1,profit:200,return_pct:.02,gap_pct:0},
                 {id:'a',name:'A',rank:2,profit:100,return_pct:.01,gap_pct:.01}];
assert.equal(score.overtaken(old, current, 'b').join(), 'A');
assert.equal(score.overtaken(current, current, 'b').length, 0);
assert.equal(score.overtaken([], current, 'b').length, 0);
assert.equal(score.overtaken(old, old, 'b').length, 0);
assert.equal(score.overtaken(current, old, 'b').length, 0);
assert.ok(score.position(current, 'a').includes('0.010 個百分點'));
assert.ok(score.position(current, 'b').includes('目前領先'));
console.log('PASS: syntax, overtakes, initial/tied/duplicate/demotion feedback, gaps');
