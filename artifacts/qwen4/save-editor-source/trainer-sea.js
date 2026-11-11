'use strict';
// 《传颂之物 虚伪的假面》人物修改器 —— SEA 单文件版
// 校验和算法源自 exe 反汇编 (fun 0x4119e0)：只校验 A(+0) 与 B(+4)，C 不参与。
const fs=require('fs');
const path=require('path');
const http=require('http');

const SAVE_DIR='<USER_HOME>/Documents/AQUAPLUS/受讚頌者 虛偽的假面/Save';
const BACKUP_DIR=path.join(path.dirname(SAVE_DIR),'修改器备份');
const CHAR_BASE=0xa4f8, CHAR_STRIDE=0x278, CHAR_SLOTS=24, MONEY_OFF=0xf8;
const PORT=8765;

const FIELDS=[
  {key:'level',off:0x00,type:'u16',label:'等级',conf:'ok',min:1,max:99},
  {key:'exp',off:0x02,type:'u16',label:'经验值',conf:'ok',min:0,max:65535},
  {key:'hp',off:0x08,type:'u32',label:'HP',conf:'ok',min:0,max:99999},
  {key:'sp',off:0x0c,type:'u32',label:'SP',conf:'ok',min:0,max:99999},
  {key:'atk',off:0x10,type:'u16',label:'攻击力',conf:'hi',min:0,max:9999},
  {key:'def',off:0x12,type:'u16',label:'防御力',conf:'hi',min:0,max:9999},
  {key:'hit',off:0x14,type:'u16',label:'命中',conf:'hi',min:0,max:999},
  {key:'avoid',off:0x16,type:'u16',label:'回避',conf:'hi',min:0,max:999},
  {key:'mov',off:0x18,type:'u16',label:'移动',conf:'hi',min:0,max:99},
  {key:'jump',off:0x1a,type:'u16',label:'跳跃',conf:'hi',min:0,max:99},
  {key:'f04',off:0x04,type:'u16',label:'字段+04',conf:'adv',min:0,max:65535},
  {key:'f1c',off:0x1c,type:'u16',label:'字段+1C',conf:'adv',min:0,max:65535},
  {key:'f24',off:0x24,type:'u16',label:'字段+24',conf:'adv',min:0,max:65535},
  {key:'f26',off:0x26,type:'u16',label:'字段+26',conf:'adv',min:0,max:65535},
  {key:'f28',off:0x28,type:'u16',label:'字段+28',conf:'adv',min:0,max:65535},
  {key:'f2a',off:0x2a,type:'u16',label:'字段+2A',conf:'adv',min:0,max:65535},
  {key:'f2c',off:0x2c,type:'u16',label:'字段+2C',conf:'adv',min:0,max:65535},
  {key:'f38',off:0x38,type:'u32',label:'字段+38',conf:'adv',min:0,max:999999},
  {key:'f3c',off:0x3c,type:'u32',label:'字段+3C',conf:'adv',min:0,max:999999},
  {key:'fc0',off:0xc0,type:'u32',label:'字段+C0',conf:'adv',min:0,max:9999999},
];
const UNIT_NAMES=/*__UNIT_NAMES__*/[];
const HTML=/*__HTML__*/'';

function checksum(buf){const n=buf.length-0x10;let sum=n>>>0,hash=1;for(let i=0x10;i<buf.length;i++){sum=(sum+buf[i])>>>0;hash=Math.imul(hash,sum)>>>0;hash=(hash+sum)>>>0;if(hash===0)hash=1;}return{A:sum,B:hash};}
function applyChecksum(buf){const c=checksum(buf);buf.writeUInt32LE(c.A,0);buf.writeUInt32LE(c.B,4);return c;}
function verifyChecksum(buf){const c=checksum(buf);return c.A===buf.readUInt32LE(0)&&c.B===buf.readUInt32LE(4);}
function readField(buf,o,f){return f.type==='u32'?buf.readUInt32LE(o+f.off):buf.readUInt16LE(o+f.off);}
function writeField(buf,o,f,v){if(f.type==='u32')buf.writeUInt32LE(v>>>0,o+f.off);else buf.writeUInt16LE(v&0xffff,o+f.off);}
function slotFile(slot){return path.join(SAVE_DIR,`GAME-${String(slot).padStart(3,'0')}.DAT`);}

function listSaves(){const out=[];if(!fs.existsSync(SAVE_DIR))return out;
  for(const name of fs.readdirSync(SAVE_DIR)){const m=name.match(/^GAME-(\d+)\.DAT$/i);if(!m)continue;
    const full=path.join(SAVE_DIR,name);const st=fs.statSync(full);
    let info={slot:+m[1],file:name,size:st.size,mtime:st.mtime.toISOString()};
    try{const buf=fs.readFileSync(full);info.valid=verifyChecksum(buf);info.money=buf.readUInt32LE(MONEY_OFF);
      let e=0x28;while(e<buf.length&&buf[e]!==0)e++;info.desc=buf.toString('utf8',0x28,e);
      info.chapter=buf.readUInt32LE(0x10c);
      info.year=buf.readUInt16LE(0x5a);info.month=buf.readUInt16LE(0x5c);info.day=buf.readUInt16LE(0x5e);
      info.hour=buf.readUInt16LE(0x60);info.min=buf.readUInt16LE(0x62);
    }catch(e){info.valid=false;}
    out.push(info);}
  out.sort((a,b)=>a.slot-b.slot);return out;}
function readSave(slot){return fs.readFileSync(slotFile(slot));}
function getCharacters(buf){const chars=[];
  for(let i=0;i<CHAR_SLOTS;i++){const off=CHAR_BASE+i*CHAR_STRIDE;if(off+CHAR_STRIDE>buf.length)break;
    const unitId=buf.readUInt32LE(off+0x270);const level=buf.readUInt16LE(off);const hp=buf.readUInt32LE(off+8);
    if(level===0&&unitId===0)continue;
    const name=UNIT_NAMES[unitId]||('单位'+unitId);const fields={};
    for(const f of FIELDS)fields[f.key]=readField(buf,off,f);
    chars.push({index:i,off,unitId,name,active:hp>0,fields});}
  return chars;}
function getMoney(buf){return buf.readUInt32LE(MONEY_OFF);}
function applyChanges(buf,changes){
  if(typeof changes.money==='number')buf.writeUInt32LE(Math.max(0,Math.min(0x7fffffff,changes.money|0)),MONEY_OFF);
  if(changes.chars){for(const k of Object.keys(changes.chars)){const off=CHAR_BASE+(+k)*CHAR_STRIDE;const vals=changes.chars[k];
    for(const f of FIELDS){if(vals[f.key]===undefined)continue;let v=Math.round(+vals[f.key]);if(!isFinite(v))continue;
      v=Math.max(f.min,Math.min(f.max,v));writeField(buf,off,f,v);}}}
  applyChecksum(buf);return buf;}
function backupSave(slot){if(!fs.existsSync(BACKUP_DIR))fs.mkdirSync(BACKUP_DIR,{recursive:true});
  const ts=new Date().toISOString().replace(/[:.]/g,'-');
  const bak=path.join(BACKUP_DIR,`GAME-${String(slot).padStart(3,'0')}_${ts}.DAT`);
  fs.copyFileSync(slotFile(slot),bak);return bak;}
function writeSave(slot,buf){applyChecksum(buf);fs.writeFileSync(slotFile(slot),buf);}

function sendJSON(res,code,obj){const b=Buffer.from(JSON.stringify(obj),'utf8');res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Content-Length':b.length});res.end(b);}
function readBody(req){return new Promise((resolve,reject)=>{let d='';req.on('data',c=>{d+=c;if(d.length>5e6){reject(new Error('body too large'));req.destroy();}});req.on('end',()=>{try{resolve(d?JSON.parse(d):{});}catch(e){reject(e);}});req.on('error',reject);});}

const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');const p=u.pathname;let m;
    if(p==='/api/saves'&&req.method==='GET')return sendJSON(res,200,{saves:listSaves(),saveDir:SAVE_DIR});
    if((m=p.match(/^\/api\/save\/(\d+)$/))&&req.method==='GET'){const slot=+m[1];const buf=readSave(slot);
      return sendJSON(res,200,{slot,valid:verifyChecksum(buf),money:getMoney(buf),chars:getCharacters(buf),fields:FIELDS});}
    if((m=p.match(/^\/api\/save\/(\d+)$/))&&req.method==='POST'){const slot=+m[1];const changes=await readBody(req);
      const bak=backupSave(slot);const buf=readSave(slot);applyChanges(buf,changes);writeSave(slot,buf);
      return sendJSON(res,200,{ok:true,backup:path.basename(bak),valid:verifyChecksum(buf),money:getMoney(buf),chars:getCharacters(buf)});}
    if((m=p.match(/^\/api\/backups\/(\d+)$/))&&req.method==='GET'){const slot=+m[1];let list=[];
      if(fs.existsSync(BACKUP_DIR))list=fs.readdirSync(BACKUP_DIR).filter(f=>f.startsWith(`GAME-${String(slot).padStart(3,'0')}_`)).sort().reverse();
      return sendJSON(res,200,{backups:list});}
    if(p==='/api/restore'&&req.method==='POST'){const{file}=await readBody(req);
      const full=path.join(BACKUP_DIR,path.basename(file));
      if(!fs.existsSync(full))return sendJSON(res,404,{error:'backup not found'});
      const mm=path.basename(file).match(/^GAME-(\d+)_/);if(!mm)return sendJSON(res,400,{error:'bad backup name'});
      const slot=+mm[1];backupSave(slot);writeSave(slot,fs.readFileSync(full));
      return sendJSON(res,200,{ok:true,slot});}
    if(p==='/'||p==='/index.html'){const b=Buffer.from(HTML,'utf8');res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Length':b.length});return res.end(b);}
    sendJSON(res,404,{error:'not found'});
  }catch(e){sendJSON(res,500,{error:String(e.message||e)});}
});
server.on('error',e=>{console.error('启动失败: '+e.message);console.error('可能端口 '+PORT+' 已被占用（修改器已在运行？）。');process.exit(1);});
server.listen(PORT,'127.0.0.1',()=>{
  console.log('传颂之物 虚伪的假面 修改器已启动: http://127.0.0.1:'+PORT);
  console.log('存档目录: '+SAVE_DIR);
  console.log('备份目录: '+BACKUP_DIR);
  if(!process.argv.includes('--no-open')){
    try{require('child_process').exec('cmd /c start "" "http://127.0.0.1:'+PORT+'"');}catch(e){}
  }
});