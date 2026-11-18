import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
const mode=process.argv[2];
const source="/home/ci/state/openclaw.json";
const store="/home/offsite";
const ns="ci-fresh-fiction";
if(mode==="configure"){
  assert(fs.existsSync(source),"Fresh fictional OpenClaw config must exist");
  assert(fs.statSync(store).isDirectory(),"Offsite directory must exist before init");
  const cfg=JSON.parse(fs.readFileSync(source,"utf8"));
  assert(!cfg.storage?.locations?.ciarchive,"Location unexpectedly already configured");
  cfg.storage={locations:{ciarchive:{
    provider:"filesystem",settings:{path:store},
    encryption:{passphrase:{source:"env",provider:"default",id:"OPENCLAW_STORAGE_PASSPHRASE"}}
  }}};
  fs.writeFileSync(source,JSON.stringify(cfg,null,2)+"\n");
  console.log("NEW_FICTIONAL_STORAGE_LOCATION_CONFIGURED_WITH_SECRET_REF=PASS");
}else if(mode==="assert-encrypted"||mode==="tamper"){
  const root=path.join(store,"backups",ns);
  assert(fs.existsSync(root),"Expected synthetic namespace missing");
  const names=fs.readdirSync(root).filter(x=>x.endsWith(".tar.gz")||x.endsWith(".tgz")||x.endsWith(".tar"));
  assert(names.length>=1,"No encrypted backup object found in fictional namespace");
  const file=path.join(root,names.sort().at(-1));
  const buf=fs.readFileSync(file);
  assert(buf.length>64 && buf.subarray(0,8).toString("utf8")==="OCSTOR1\n",
    "OpenClaw ciphertext magic mismatch");
  assert(!buf.includes(Buffer.from("FICTION_ONLY\n")),"Plaintext marker exposed");
  assert(!buf.includes(Buffer.from("NEW_INSTALL_FICTION_ONLY")),"Plaintext workspace exposed");
  console.log("OFFSITE_BACKUP_IS_OPENCLAW_AUTHENTICATED_CIPHERTEXT=PASS");
  console.log("OFFSITE_BACKUP_DOES_NOT_EXPOSE_SYNTHETIC_PLAINTEXT=PASS");
  if(mode==="tamper"){
    const fd=fs.openSync(file,"r+");
    try{
      const pos=buf.length-1;
      const b=Buffer.from([buf[pos]^1]);
      assert.equal(fs.writeSync(fd,b,0,1,pos),1);
    }finally{fs.closeSync(fd)}
    console.log("FICTIONAL_OFFSITE_CIPHERTEXT_INTENTIONALLY_TAMPERED=PASS");
  }
}else if(mode==="seed-retention"){
  const dir=path.join(store,"backups",ns);
  const keys=fs.readdirSync(dir).filter(x=>/^\d{8}T\d{6}Z-[a-f0-9]{8}\.tar\.gz$/.test(x));
  assert.equal(keys.length,1,"Expected exactly one original archive before retention");
  fs.writeFileSync(path.join(dir,"keep-nonbackup.txt"),"FAKE_NONBACKUP_NOTE\n");
  const other=path.join(store,"backups","ci-unrelated-fiction");
  fs.mkdirSync(other,{recursive:true});
  fs.writeFileSync(path.join(other,"20260101T000000Z-aaaaaaaa.tar.gz"),"FAKE_OTHER_NAMESPACE\n");
  console.log("FICTION_RETENTION_SEEDED=PASS");
}else if(mode==="assert-retention"){
  const dir=path.join(store,"backups",ns);
  const keys=fs.readdirSync(dir).filter(x=>/^\d{8}T\d{6}Z-[a-f0-9]{8}\.tar\.gz$/.test(x));
  assert.equal(keys.length,1,"Retention failed to leave exactly newest archive from UTC day");
  assert(fs.existsSync(path.join(dir,"owner.json")),"Owner claim was deleted");
  assert.equal(fs.readFileSync(path.join(dir,"keep-nonbackup.txt"),"utf8"),"FAKE_NONBACKUP_NOTE\n","Non-backup key deleted or overwritten");
  assert.equal(fs.readFileSync(path.join(store,"backups","ci-unrelated-fiction","20260101T000000Z-aaaaaaaa.tar.gz"),"utf8"),"FAKE_OTHER_NAMESPACE\n","Other namespace modified");
  console.log("NATIVE_RETENTION_NEWEST_ONLY_OWNER_AND_UNRELATED_OBJECTS_PRESERVED=PASS");
}else if(mode==="seed-crossdate"){
  const dir=path.join(store,"backups",ns),rx=/^\d{8}T\d{6}Z-[a-f0-9]{8}\.tar\.gz$/;
  const existing=fs.readdirSync(dir).filter(k=>rx.test(k));
  assert.equal(existing.length,1,"Require exactly one new native encrypted archive");
  const newest=existing[0],ciphertext=fs.readFileSync(path.join(dir,newest));
  assert.equal(ciphertext.subarray(0,8).toString("utf8"),"OCSTOR1\n");
  const now=new Date(),y=now.getUTCFullYear(),m=now.getUTCMonth(),day=now.getUTCDate();
  const stamp=d=>d.toISOString().replace(/[-:]/g,"").replace(/\.\d{3}Z$/,"Z");
  let id=1;
  const key=d=>stamp(d)+"-"+(id++).toString(16).padStart(8,"0")+".tar.gz";
  const historical=[];
  for(let i=1;i<=11;i++)historical.push(key(new Date(Date.UTC(y,m,day-i,12))));
  const weekday=(now.getUTCDay()+6)%7;
  for(let i=1;i<=9;i++)historical.push(key(new Date(Date.UTC(y,m,day-weekday-7*i,10))));
  for(let i=1;i<=16;i++)historical.push(key(new Date(Date.UTC(y,m-i,1,12))));
  historical.push(key(new Date(Date.UTC(y,m,day-4,14))));
  historical.push(key(new Date(Date.UTC(y,m,day-4,15))));
  const all=[newest,...historical].sort().reverse();
  assert.equal(new Set(all).size,all.length);
  assert.equal(all[0],newest,"Real backup must be newest");
  const date=k=>new Date(k.slice(0,4)+"-"+k.slice(4,6)+"-"+k.slice(6,8)+"T"+
    k.slice(9,11)+":"+k.slice(11,13)+":"+k.slice(13,15)+"Z");
  const bucket=(k,p)=>{
    const d=date(k),day=d.toISOString().slice(0,10);
    if(p==="day")return day;
    if(p==="month")return day.slice(0,7);
    d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
    return d.toISOString().slice(0,10);
  };
  for(const [p,count] of [["day",7],["week",4],["month",12]]){
    assert(new Set(all.map(k=>bucket(k,p))).size>count,"Fixture lacks calendar coverage");
  }
  const keep=new Set([newest]);
  for(const [p,count] of [["day",7],["week",4],["month",12]]){
    const seen=new Set();
    for(const k of all){const b=bucket(k,p);if(seen.size<count && !seen.has(b)){seen.add(b);keep.add(k)}}
    assert.equal(seen.size,count);
  }
  const expectedKept=all.filter(k=>keep.has(k)),expectedDeleted=all.filter(k=>!keep.has(k));
  assert(expectedKept.length>=12 && expectedDeleted.length>=12);
  for(const k of historical)fs.copyFileSync(path.join(dir,newest),path.join(dir,k),fs.constants.COPYFILE_EXCL);
  const manifest={newest,expectedKept,expectedDeleted,oldKey:expectedKept.find(k=>k!==newest)};
  fs.writeFileSync(path.join(dir,"crossdate-fixture.json"),JSON.stringify(manifest));
  console.log("FICTION_CROSSDATE_CIPHERTEXT_SEEDED=PASS total="+all.length+
    " kept="+expectedKept.length+" deleted="+expectedDeleted.length);
}else if(mode==="assert-crossdate"||mode==="old-key"){
  const dir=path.join(store,"backups",ns);
  const manifest=JSON.parse(fs.readFileSync(path.join(dir,"crossdate-fixture.json"),"utf8"));
  const rx=/^\d{8}T\d{6}Z-[a-f0-9]{8}\.tar\.gz$/;
  const actual=fs.readdirSync(dir).filter(k=>rx.test(k)).sort();
  assert.deepEqual(actual,manifest.expectedKept.slice().sort(),"Native UTC calendar retention mismatch");
  assert(manifest.expectedDeleted.every(k=>!fs.existsSync(path.join(dir,k))));
  assert(fs.existsSync(path.join(dir,"owner.json")));
  assert.equal(fs.readFileSync(path.join(dir,"keep-nonbackup.txt"),"utf8"),"FAKE_NONBACKUP_NOTE\n");
  assert.equal(fs.readFileSync(path.join(store,"backups","ci-unrelated-fiction","20260101T000000Z-aaaaaaaa.tar.gz"),"utf8"),"FAKE_OTHER_NAMESPACE\n");
  if(mode==="old-key")process.stdout.write(manifest.oldKey+"\n");
  else console.log("NATIVE_CROSSDATE_EXACT_7D_4W_12M_AND_FOREIGN_PRESERVATION=PASS kept="+actual.length+
    " deleted="+manifest.expectedDeleted.length);
}else{
  throw Error("Unknown fictional storage test mode");
}
