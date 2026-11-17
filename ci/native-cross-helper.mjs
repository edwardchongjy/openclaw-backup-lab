import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const mode=process.argv[2];
const home='/home/ci', store='/home/offsite';
const hash=b=>createHash('sha256').update(b).digest('hex');
const expected=store+'/expected-fictional-sha256.json';
const corpus={
 'workspace/cross-fixture/empty.txt':Buffer.alloc(0),
 'workspace/cross-fixture/nested/message.txt':Buffer.from('CROSS_ENV_FICTION_ONLY_20261117\n'),
 'workspace/cross-fixture/繁體中文 空格.txt':Buffer.from('全新虛構復原測試，沒有真實資料。\n'),
 'workspace/cross-fixture/binary.bin':Buffer.from(Array.from({length:4096},(_,i)=>i%256)),
 'state/cross-fixture.json':Buffer.from('{"fictional":true,"version":1}\n')
};
const walk=(root)=>fs.readdirSync(root,{withFileTypes:true}).flatMap(x=>{
 const p=path.join(root,x.name); assert(!x.isSymbolicLink());
 return x.isDirectory()?walk(p):[p];
});
if(mode==='seed'){
 for(const [n,b] of Object.entries(corpus)){
  const p=path.join(home,n); assert(!fs.existsSync(p));
  fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,b);
 }
 const selected=[...Object.keys(corpus),'state/openclaw.json','state/fictional-proof.txt','workspace/persisted-fake-note.txt'];
 const rows=Object.fromEntries(selected.map(n=>{const b=fs.readFileSync(path.join(home,n));return [n,{size:b.length,sha256:hash(b)}]}));
 fs.writeFileSync(expected,JSON.stringify(rows,null,2)+'\n');
 console.log('PRE_BACKUP_INDEPENDENT_EXPECTED_CORPUS_SHA256_8_FILES=PASS');
}else if(mode==='audit-export'){
 const files=walk(store); assert(files.length>2 && files.length<50);
 let ciphertext=0;
 for(const p of files){
  const b=fs.readFileSync(p); assert(b.length<8*1024*1024);
  assert(!b.includes(Buffer.from(process.env.OPENCLAW_STORAGE_PASSPHRASE)),'test passphrase present in export');
  if(p.endsWith('.tar.gz')){
   assert.equal(b.subarray(0,8).toString(),'OCSTOR1\n');ciphertext++;
   for(const fixture of Object.values(corpus)) if(fixture.length>8) assert(!b.includes(fixture));
  }else{
   for(const fixture of Object.values(corpus)) if(fixture.length>8) assert(!b.includes(fixture),'plaintext fixture exported');
  }
 }
 assert.equal(ciphertext,1);
 console.log('EXPORTED_STORAGE_NO_PASSPHRASE_OR_PLAINTEXT_CORPUS=PASS');
 console.log('EXPORTED_STORAGE_SINGLE_NATIVE_OCSTOR1_CIPHERTEXT=PASS');
}else if(mode==='recovery-config'){
 assert(!fs.existsSync(home+'/state'),'second runner state not fresh');
 assert(!fs.existsSync(home+'/workspace'),'source workspace unexpectedly present');
 assert(fs.existsSync(expected));
 fs.mkdirSync(home+'/state',{recursive:true});
 fs.writeFileSync(home+'/state/openclaw.json',JSON.stringify({storage:{locations:{ciarchive:{provider:'filesystem',settings:{path:store},encryption:{passphrase:{source:'env',provider:'default',id:'OPENCLAW_STORAGE_PASSPHRASE'}}}}}}));
 console.log('SECOND_RUNNER_NO_SOURCE_STATE_OR_AGENT_BEFORE_RESTORE=PASS');
 console.log('SECOND_RUNNER_RECOVERY_ONLY_STORAGE_CONFIG_CREATED=PASS');
}else if(mode==='compare'){
 const root=home+'/restored';
 const dirs=fs.readdirSync(root); assert.equal(dirs.length,1);
 const payload=path.join(root,dirs[0],'payload/posix/home/ci');
 const rows=JSON.parse(fs.readFileSync(expected,'utf8')); assert.equal(Object.keys(rows).length,8);
 for(const [n,e] of Object.entries(rows)){
  const b=fs.readFileSync(path.join(payload,n)); assert.equal(b.length,e.size,n);assert.equal(hash(b),e.sha256,n);
  console.log('RESTORED_FILE_SHA256 '+JSON.stringify(n)+' '+e.sha256);
 }
 const cfg=JSON.parse(fs.readFileSync(path.join(payload,'state/openclaw.json'),'utf8'));
 assert(cfg.agents.list.some(a=>a.id==='ci-contained'));
 console.log('SOURCE_AND_RESTORED_CORPUS_CONFIG_8_OF_8_SHA256_MATCH=PASS');
 console.log('RESTORED_CONFIG_RETAINS_FICTIONAL_AGENT=PASS');
 assert(!fs.existsSync(home+'/workspace'),'restore activated source workspace');
 console.log('RESTORE_STAGING_ONLY_NO_ACTIVATION=PASS');
}else if(mode==='check-wrong-empty'||mode==='check-tamper-empty'){
 const p=home+(mode==='check-wrong-empty'?'/wrong-target':'/tamper-target');
 assert(!fs.existsSync(p)||fs.readdirSync(p).length===0);
 console.log((mode==='check-wrong-empty'?'WRONG_KEY':'TAMPER')+'_REJECTION_LEFT_NO_RESTORED_FILES=PASS');
}else throw Error('unknown mode');
