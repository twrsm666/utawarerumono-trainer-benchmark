'use strict';
const fs=require('fs');
const {execSync}=require('child_process');
const names=JSON.parse(fs.readFileSync('unit_names.json','utf8'));
const html=fs.readFileSync('public/index.html','utf8');
let src=fs.readFileSync('trainer-sea.js','utf8');
if(!src.includes('/*__UNIT_NAMES__*/[]')||!src.includes("/*__HTML__*/''")){throw new Error('placeholders missing');}
src=src.replace('/*__UNIT_NAMES__*/[]',JSON.stringify(names));
src=src.replace("/*__HTML__*/''",JSON.stringify(html));
fs.writeFileSync('trainer-bundle.js',src);
fs.writeFileSync('sea-config.json',JSON.stringify({main:'trainer-bundle.js',output:'trainer.blob',disableExperimentalSEAWarning:true},null,2));
console.log('bundle bytes='+src.length);
execSync('node --experimental-sea-config sea-config.json',{stdio:'inherit'});
console.log('blob bytes='+fs.statSync('trainer.blob').size);