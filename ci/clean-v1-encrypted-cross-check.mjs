import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const [mode,arg,arg2]=process.argv.slice(2);
const digest=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function files(root){
 const out=[];
 for(const e of fs.readdirSync(root,{withFileTypes:true})){
  const p=path.join(root,e.name); assert(!e.isSymbolicLink());
  if(e.isDirectory())out.push(...files(p));else {assert(e.isFile());out.push(p);}
 }
 return out.sort();
}
if(mode==='manifest'){
 const list=['/home/ci/state/openclaw.json','/home/ci/state/fictional-proof.txt',...files('/home/ci/workspace')];
 assert(list.length>=3);
 console.log(JSON.stringify(Object.fromEntries(list.sort().map(p=>[p,digest(p)]))));
}else if(mode==='compare'){
 const roots=fs.readdirSync(arg);assert.equal(roots.length,1);
 const payload=path.join(arg,roots[0],'payload','posix');
 const expected=JSON.parse(fs.readFileSync(arg2,'utf8'));
 const count=Object.keys(expected).length;assert(count>=3);
 for(const [p,hash] of Object.entries(expected)){
  assert(p==='/home/ci/state/openclaw.json'||p==='/home/ci/state/fictional-proof.txt'||p.startsWith('/home/ci/workspace/'));
  const restored=path.join(payload,p.slice(1));assert.equal(digest(restored),hash,p);
 }
 const workspace=files(path.join(payload,'home/ci/workspace')).map(p=>'/'+path.relative(payload,p)).sort();
 assert.deepEqual(workspace,Object.keys(expected).filter(p=>p.startsWith('/home/ci/workspace/')).sort());
 console.log(`SECOND_HOST_CONFIG_FIXTURE_AND_ALL_WORKSPACE_SHA256=PASS files=${count}`);
 console.log('SCOPE=static config, sentinel and complete workspace; mutable state SQLite snapshot is not byte-compared');
}else if(mode==='no-plaintext'){
 for(const p of files('/home/offsite')){
  const b=fs.readFileSync(p);
  for(const marker of ['PUBLIC_LAB_KEY_NOT_SECRET_DO_NOT_USE_FOR_REAL_OPENCLAW','FICTION_ONLY\n','NEW_INSTALL_FICTION_ONLY','FICTIONAL-PLACEHOLDER-NOT-A-KEY'])assert(!b.includes(Buffer.from(marker)),p);
 }
 console.log('TRANSFER_STORE_NO_KNOWN_PLAINTEXT_OR_DUMMY_PASSPHRASE=PASS');
}else if(mode==='reject'){
 assert(['wrong','tamper'].includes(arg));
 const target='/tmp/rejected-'+arg;assert(!fs.existsSync(target));
 const r=spawnSync(process.execPath,['/app/upstream/openclaw.mjs','backup','restore','--from','ciarchive','--namespace','ci-fresh-fiction','latest','--target',target],{env:process.env,encoding:'utf8',timeout:180000,maxBuffer:4*1024*1024});
 assert(!r.error);assert(r.status!==null&&r.status!==0);
 const output=String(r.stdout)+String(r.stderr);
 assert(/decrypt|authenticat|passphrase|cipher|bad decrypt/i.test(output),'Failure must identify cryptographic rejection');
 assert(!fs.existsSync(target)||files(target).length===0,'Rejected restore left plaintext files');
 console.log(`SECOND_HOST_${arg.toUpperCase()}_RESTORE_REJECTED_WITH_NO_OUTPUT=PASS exit=${r.status}`);
}else throw Error('Unknown test mode');
