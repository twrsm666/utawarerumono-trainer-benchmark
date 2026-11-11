'use strict';
// 《传颂之物 虚伪的假面》存档引擎
// 校验和算法已由 exe 反汇编确认 (fun 0x4119e0): 只校验 A(+0) 与 B(+4)，C(+0xC) 不参与校验。
const fs = require('fs');
const path = require('path');

const SAVE_DIR = '<USER_HOME>/Documents/AQUAPLUS/受讚頌者 虛偽的假面/Save';
const CHAR_BASE = 0xa4f8;      // 人物数组起点
const CHAR_STRIDE = 0x278;     // 每条人物记录字节数
const CHAR_SLOTS = 24;         // 槽位数
const MONEY_OFF = 0xf8;        // 金钱

// 人物属性字段定义（offset 相对记录起点）。conf: 已验证 / 高置信 / 进阶
const FIELDS = [
  { key:'level', off:0x00, type:'u16', label:'等级', conf:'ok',   min:1,  max:99 },
  { key:'exp',   off:0x02, type:'u16', label:'经验值', conf:'ok', min:0,  max:65535 },
  { key:'hp',    off:0x08, type:'u32', label:'HP',  conf:'ok',   min:0,  max:99999 },
  { key:'sp',    off:0x0c, type:'u32', label:'SP',  conf:'ok',   min:0,  max:99999 },
  { key:'atk',   off:0x10, type:'u16', label:'攻击力', conf:'hi', min:0,  max:9999 },
  { key:'def',   off:0x12, type:'u16', label:'防御力', conf:'hi', min:0,  max:9999 },
  { key:'hit',   off:0x14, type:'u16', label:'命中',  conf:'hi', min:0,  max:999 },
  { key:'avoid', off:0x16, type:'u16', label:'回避',  conf:'hi', min:0,  max:999 },
  { key:'mov',   off:0x18, type:'u16', label:'移动',  conf:'hi', min:0,  max:99 },
  { key:'jump',  off:0x1a, type:'u16', label:'跳跃',  conf:'hi', min:0,  max:99 },
  // 进阶字段（可编辑，标注偏移）
  { key:'f04', off:0x04, type:'u16', label:'字段+04', conf:'adv', min:0, max:65535 },
  { key:'f1c', off:0x1c, type:'u16', label:'字段+1C', conf:'adv', min:0, max:65535 },
  { key:'f24', off:0x24, type:'u16', label:'字段+24', conf:'adv', min:0, max:65535 },
  { key:'f26', off:0x26, type:'u16', label:'字段+26', conf:'adv', min:0, max:65535 },
  { key:'f28', off:0x28, type:'u16', label:'字段+28', conf:'adv', min:0, max:65535 },
  { key:'f2a', off:0x2a, type:'u16', label:'字段+2A', conf:'adv', min:0, max:65535 },
  { key:'f2c', off:0x2c, type:'u16', label:'字段+2C', conf:'adv', min:0, max:65535 },
  { key:'f38', off:0x38, type:'u32', label:'字段+38', conf:'adv', min:0, max:999999 },
  { key:'f3c', off:0x3c, type:'u32', label:'字段+3C', conf:'adv', min:0, max:999999 },
  { key:'fc0', off:0xc0, type:'u32', label:'字段+C0', conf:'adv', min:0, max:9999999 },
];

let UNIT_NAMES = [];
try { UNIT_NAMES = JSON.parse(fs.readFileSync(path.join(__dirname,'unit_names.json'),'utf8')); } catch(e){ UNIT_NAMES = []; }

function checksum(buf){
  const n = buf.length - 0x10;
  let sum = n>>>0, hash = 1;
  for(let i=0x10;i<buf.length;i++){
    sum = (sum + buf[i])>>>0;
    hash = Math.imul(hash, sum)>>>0;
    hash = (hash + sum)>>>0;
    if(hash===0) hash = 1;
  }
  return { A:sum, B:hash };
}
function applyChecksum(buf){
  const c = checksum(buf);
  buf.writeUInt32LE(c.A, 0);
  buf.writeUInt32LE(c.B, 4);
  return c;
}
function verifyChecksum(buf){
  const c = checksum(buf);
  return c.A===buf.readUInt32LE(0) && c.B===buf.readUInt32LE(4);
}
function readField(buf, recOff, f){
  const o = recOff + f.off;
  return f.type==='u32' ? buf.readUInt32LE(o) : buf.readUInt16LE(o);
}
function writeField(buf, recOff, f, val){
  const o = recOff + f.off;
  if(f.type==='u32') buf.writeUInt32LE(val>>>0, o); else buf.writeUInt16LE(val & 0xffff, o);
}

function listSaves(){
  const out=[];
  if(!fs.existsSync(SAVE_DIR)) return out;
  for(const name of fs.readdirSync(SAVE_DIR)){
    const m = name.match(/^GAME-(\d+)\.DAT$/i);
    if(!m) continue;
    const full = path.join(SAVE_DIR,name);
    const st = fs.statSync(full);
    let info = { slot:+m[1], file:name, size:st.size, mtime:st.mtime.toISOString() };
    try{
      const buf = fs.readFileSync(full);
      info.valid = verifyChecksum(buf);
      info.money = buf.readUInt32LE(MONEY_OFF);
      // 描述字符串 @0x28
      let e=0x28; while(e<buf.length && buf[e]!==0) e++;
      info.desc = buf.toString('utf8',0x28,e);
      info.chapter = buf.readUInt32LE(0x10c);
      // 日期 @0x5a 起，各 u16
      info.year=buf.readUInt16LE(0x5a); info.month=buf.readUInt16LE(0x5c); info.day=buf.readUInt16LE(0x5e);
      info.hour=buf.readUInt16LE(0x60); info.min=buf.readUInt16LE(0x62);
    }catch(e){ info.valid=false; }
    out.push(info);
  }
  out.sort((a,b)=>a.slot-b.slot);
  return out;
}

function readSave(slot){
  const file = path.join(SAVE_DIR, `GAME-${String(slot).padStart(3,'0')}.DAT`);
  const buf = fs.readFileSync(file);
  return buf;
}

function getCharacters(buf){
  const chars=[];
  for(let i=0;i<CHAR_SLOTS;i++){
    const off = CHAR_BASE + i*CHAR_STRIDE;
    if(off+CHAR_STRIDE>buf.length) break;
    const unitId = buf.readUInt32LE(off+0x270);
    const level = buf.readUInt16LE(off);
    const hp = buf.readUInt32LE(off+8);
    // 空槽：等级0 且 无单位ID
    if(level===0 && unitId===0) continue;
    const name = UNIT_NAMES[unitId] || ('单位'+unitId);
    const fields={};
    for(const f of FIELDS) fields[f.key]=readField(buf,off,f);
    chars.push({ index:i, off, unitId, name, active: hp>0, fields });
  }
  return chars;
}

function getMoney(buf){ return buf.readUInt32LE(MONEY_OFF); }

// 应用修改：changes = { money?, chars: { [index]: {fieldKey:value} } }
function applyChanges(buf, changes){
  if(typeof changes.money==='number'){
    buf.writeUInt32LE(Math.max(0,Math.min(0x7fffffff, changes.money|0)), MONEY_OFF);
  }
  if(changes.chars){
    for(const idxStr of Object.keys(changes.chars)){
      const idx=+idxStr;
      const off=CHAR_BASE+idx*CHAR_STRIDE;
      const vals=changes.chars[idxStr];
      for(const f of FIELDS){
        if(vals[f.key]===undefined) continue;
        let v=Math.round(+vals[f.key]);
        if(!isFinite(v)) continue;
        v=Math.max(f.min, Math.min(f.max, v));
        writeField(buf,off,f,v);
      }
    }
  }
  applyChecksum(buf);
  return buf;
}

function backupSave(slot){
  const file=path.join(SAVE_DIR,`GAME-${String(slot).padStart(3,'0')}.DAT`);
  const bakDir=path.join(__dirname,'backups');
  if(!fs.existsSync(bakDir)) fs.mkdirSync(bakDir,{recursive:true});
  const ts=new Date().toISOString().replace(/[:.]/g,'-');
  const bak=path.join(bakDir,`GAME-${String(slot).padStart(3,'0')}_${ts}.DAT`);
  fs.copyFileSync(file,bak);
  return bak;
}

function writeSave(slot, buf){
  const file=path.join(SAVE_DIR,`GAME-${String(slot).padStart(3,'0')}.DAT`);
  applyChecksum(buf);
  fs.writeFileSync(file, buf);
}

module.exports={ SAVE_DIR, FIELDS, CHAR_BASE, CHAR_STRIDE, MONEY_OFF,
  checksum, applyChecksum, verifyChecksum, listSaves, readSave, getCharacters,
  getMoney, applyChanges, backupSave, writeSave, UNIT_NAMES };