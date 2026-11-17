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
}else{
  throw Error("Unknown fictional storage test mode");
}
