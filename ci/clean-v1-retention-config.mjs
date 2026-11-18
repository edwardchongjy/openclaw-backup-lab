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
}else{
  throw Error("Unknown fictional storage test mode");
}
