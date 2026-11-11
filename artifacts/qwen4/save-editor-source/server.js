'use strict';
const http=require('http');
const fs=require('fs');
const path=require('path');
const E=require('./saveengine');
const PORT=8765;
const PUB=path.join(__dirname,'public');
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.png':'image/png','.svg':'image/svg+xml'};

function sendJSON(res,code,obj){const b=Buffer.from(JSON.stringify(obj),'utf8');res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Content-Length':b.length});res.end(b);}
function readBody(req){return new Promise((resolve,reject)=>{let d='';req.on('data',c=>{d+=c;if(d.length>5e6){reject(new Error('body too large'));req.destroy();}});req.on('end',()=>{try{resolve(d?JSON.parse(d):{});}catch(e){reject(e);}});req.on('error',reject);});}

const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');
    const p=u.pathname;
    if(p==='/api/saves'&&req.method==='GET'){return sendJSON(res,200,{saves:E.listSaves(),saveDir:E.SAVE_DIR});}
    let m;
    if((m=p.match(/^\/api\/save\/(\d+)$/))&&req.method==='GET'){
      const slot=+m[1];const buf=E.readSave(slot);
      return sendJSON(res,200,{slot,valid:E.verifyChecksum(buf),money:E.getMoney(buf),chars:E.getCharacters(buf),fields:E.FIELDS});
    }
    if((m=p.match(/^\/api\/save\/(\d+)$/))&&req.method==='POST'){
      const slot=+m[1];const changes=await readBody(req);
      const bak=E.backupSave(slot);
      const buf=E.readSave(slot);
      E.applyChanges(buf,changes);
      E.writeSave(slot,buf);
      return sendJSON(res,200,{ok:true,backup:path.basename(bak),valid:E.verifyChecksum(buf),money:E.getMoney(buf),chars:E.getCharacters(buf)});
    }
    if((m=p.match(/^\/api\/backups\/(\d+)$/))&&req.method==='GET'){
      const slot=+m[1];const dir=path.join(__dirname,'backups');
      let list=[];
      if(fs.existsSync(dir)){list=fs.readdirSync(dir).filter(f=>f.startsWith(`GAME-${String(slot).padStart(3,'0')}_`)).sort().reverse();}
      return sendJSON(res,200,{backups:list});
    }
    if(p==='/api/restore'&&req.method==='POST'){
      const {file}=await readBody(req);
      const dir=path.join(__dirname,'backups');
      const full=path.join(dir,path.basename(file));
      if(!fs.existsSync(full))return sendJSON(res,404,{error:'backup not found'});
      const mm=path.basename(file).match(/^GAME-(\d+)_/);
      if(!mm)return sendJSON(res,400,{error:'bad backup name'});
      const slot=+mm[1];
      E.backupSave(slot); // safety backup of current before restore
      const data=fs.readFileSync(full);
      E.writeSave(slot,data);
      return sendJSON(res,200,{ok:true,slot});
    }
    // static
    let fp=p==='/'?'/index.html':p;
    const full=path.join(PUB,path.normalize(fp));
    if(!full.startsWith(PUB))return sendJSON(res,403,{error:'forbidden'});
    if(fs.existsSync(full)&&fs.statSync(full).isFile()){
      const ext=path.extname(full);const data=fs.readFileSync(full);
      res.writeHead(200,{'Content-Type':MIME[ext]||'application/octet-stream','Content-Length':data.length});
      return res.end(data);
    }
    sendJSON(res,404,{error:'not found'});
  }catch(e){
    sendJSON(res,500,{error:String(e.message||e)});
  }
});
server.listen(PORT,'127.0.0.1',()=>{
  console.log('修改器已启动: http://127.0.0.1:'+PORT);
  console.log('存档目录: '+E.SAVE_DIR);
  if(process.argv.includes('--open')){
    require('child_process').exec('cmd /c start "" "http://127.0.0.1:'+PORT+'"');
  }
});