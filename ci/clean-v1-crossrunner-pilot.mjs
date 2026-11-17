import fs from "node:fs";
import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import net from "node:net";
import {setTimeout as delay} from "node:timers/promises";
const HOME="/home/ci";
const mode=process.env.CI_PILOT_MODE;
assert(["first","restart","seed-corrupt"].includes(mode),"Unknown synthetic pilot mode");
const SRC="/app/upstream";
const entry=SRC+"/openclaw.mjs";
const fake=SRC+"/ci-fake-provider.mjs";
const TRUE_RESPONSE="FULL_CONTAINER_FAKE_REPLY_20261117";
const env={
  PATH:"/usr/local/bin:/usr/bin:/bin",HOME,
  TMPDIR:"/tmp",XDG_CONFIG_HOME:HOME+"/.config",XDG_CACHE_HOME:HOME+"/cache",
  OPENCLAW_HOME:HOME,OPENCLAW_STATE_DIR:HOME+"/state",
  OPENCLAW_CONFIG_PATH:HOME+"/state/openclaw.json",
  OPENCLAW_GATEWAY_PORT:"18991",OPENCLAW_GATEWAY_TOKEN:"PUBLIC-CI-FICTION-NOT-SECRET",
  OPENCLAW_DISABLE_BUNDLED_PLUGINS:"1",CI:"true",NO_COLOR:"1",
  NODE_DISABLE_COMPILE_CACHE:"1", CI_PILOT_MODE:mode
};
const trace=(name)=>console.log(name+"=PASS");
const children=[];
const exitChildren=()=>{for(const child of children){try{child.kill("SIGTERM")}catch{}}};
process.on("SIGTERM",exitChildren);
const run=(...args)=>{
  const r=spawnSync(process.execPath,[entry,...args],{
    env,cwd:SRC,encoding:"utf8",timeout:180000,maxBuffer:8*1024*1024
  });
  if(r.status!==0){
    throw new Error("OpenClaw CLI "+args.slice(0,2).join(" ")+" failed: "+
      String(r.error?.message||r.stderr||r.stdout).slice(-1000));
  }
  return r.stdout;
};
const fork=(cmd,args)=>{
  let output="";
  const child=spawn(cmd,args,{env,cwd:SRC,stdio:["ignore","pipe","pipe"]});
  child.stdout.on("data",x=>{output=(output+x.toString()).slice(-20000)});
  child.stderr.on("data",x=>{output=(output+x.toString()).slice(-20000)});
  child.getOutput=()=>output;
  children.push(child);return child;
};
const ready=async(url,child)=>{
  for(let i=0;i<80;i++){
    if(child.exitCode!==null)throw new Error("Service exited "+String(child.exitCode)+" "+child.getOutput().slice(-800));
    try{const r=await fetch(url,{signal:AbortSignal.timeout(1800)});if(r.ok)return}catch{}
    await delay(1500);
  }
  throw new Error("Service not ready "+url+" "+child.getOutput().slice(-1000));
};
const outbound=async(host,family)=>{
  const err=await new Promise(resolve=>{
    const s=net.connect({host,port:443,family,timeout:2500});
    s.on("connect",()=>{s.destroy();resolve("CONNECTED")});
    s.on("error",e=>{s.destroy();resolve(e.code||"OTHER")});
    s.on("timeout",()=>{s.destroy();resolve("TIMEOUT")});
  });
  assert(["ENETUNREACH","EHOSTUNREACH","EAFNOSUPPORT","ENODEV"].includes(err),"outbound was not conclusively denied: "+err);
};
try{
  assert.equal(process.getuid(),10001);trace("REAL_OPENCLAW_CONTAINER_NONROOT_UID");
  assert.equal(process.versions.node,"24.16.0");trace("REAL_OPENCLAW_CONTAINER_PINNED_NODE");
  assert(!fs.existsSync(process.env.HOST_ONLY_FICTION_PATH));trace("REAL_OPENCLAW_CONTAINER_HOST_MARKER_UNSEEN");
  assert(!fs.existsSync("/var/run/docker.sock"));trace("REAL_OPENCLAW_CONTAINER_NO_DOCKER_SOCKET");
  assert.throws(()=>fs.writeFileSync(SRC+"/ci-should-not-write.txt","BAD"));
  trace("REAL_OPENCLAW_CONTAINER_READ_ONLY_SOURCE");
  fs.mkdirSync(HOME+"/state",{recursive:true});
  fs.mkdirSync(HOME+"/workspace",{recursive:true});
  fs.mkdirSync(HOME+"/cache",{recursive:true});
  if(mode==="seed-corrupt"){
    fs.writeFileSync(HOME+"/state/fictional-proof.txt","BAD_MARKER\n");
    fs.writeFileSync(HOME+"/state/openclaw.json","{invalid-fiction-json");
    trace("INTENTIONALLY_CORRUPTED_NEW_VOLUME_CREATED");
    process.exit(0);
  }
  if(mode==="first"){
    assert(!fs.existsSync(HOME+"/state/openclaw.json"),"New data volume unexpectedly contains config");
    fs.writeFileSync(HOME+"/state/fictional-proof.txt","FICTION_ONLY\n");
    fs.writeFileSync(HOME+"/workspace/persisted-fake-note.txt","NEW_INSTALL_FICTION_ONLY\n");
    trace("NEW_VOLUME_STARTED_EMPTY_AND_SEEDED");
  }else{
    assert.equal(fs.readFileSync(HOME+"/state/fictional-proof.txt","utf8"),
      "FICTION_ONLY\n","PERSISTED_STATE_INTEGRITY_BLOCKED");
    assert.equal(fs.readFileSync(HOME+"/workspace/persisted-fake-note.txt","utf8"),
      "NEW_INSTALL_FICTION_ONLY\n","PERSISTED_WORKSPACE_INTEGRITY_BLOCKED");
    assert.doesNotThrow(()=>JSON.parse(fs.readFileSync(HOME+"/state/openclaw.json","utf8")),
      "PERSISTED_CONFIG_JSON_INTEGRITY_BLOCKED");
    trace("RESTARTED_STATE_AND_WORKSPACE_PROVEN_SAME");
  }
  trace("REAL_OPENCLAW_CONTAINER_SCOPED_WRITABLE_STATE");
  await outbound("192.0.2.1",4);trace("REAL_OPENCLAW_CONTAINER_IPV4_NO_EGRESS");
  await outbound("2001:db8::1",6);trace("REAL_OPENCLAW_CONTAINER_IPV6_NO_EGRESS");
  const version=run("--version");
  assert(version.includes("2026.10.5"));trace("REAL_OPENCLAW_CONTAINER_VERSION");
  if(mode==="first"){
    run("setup","--baseline","--skip-bootstrap","--workspace",HOME+"/workspace","--json");
    run("agents","add","ci-contained","--workspace",HOME+"/workspace/ci-contained","--non-interactive","--json");
    const configPath=env.OPENCLAW_CONFIG_PATH;
  const c=JSON.parse(fs.readFileSync(configPath,"utf8"));
  c.models={mode:"replace",providers:{"ci-fake":{
    baseUrl:"http://127.0.0.1:19042/v1",
    apiKey:"FICTIONAL-PLACEHOLDER-NOT-A-KEY",api:"openai-completions",
    models:[{id:"fake-echo",name:"Isolated Fake Provider",
      reasoning:false,input:["text"],contextWindow:32768,maxTokens:256,
      cost:{input:0,output:0,cacheRead:0,cacheWrite:0},
      compat:{supportsTools:false,supportsUsageInStreaming:false}}]
  }}};
  if(!c.agents)c.agents={};
  if(!c.agents.defaults)c.agents.defaults={};
  c.agents.defaults.model={primary:"ci-fake/fake-echo"};
  fs.writeFileSync(configPath,JSON.stringify(c,null,2)+"\n");
    trace("NEW_OPENCLAW_CONFIG_STORED_IN_FRESH_VOLUME");
  }else{
    assert(fs.existsSync(env.OPENCLAW_CONFIG_PATH),"PERSISTED_CONFIG_MISSING");
  }
  const agents=JSON.parse(run("agents","list","--json"));
  assert(Array.isArray(agents)&&agents.some(a=>a.id==="ci-contained"));
  trace(mode==="first"?"NEW_OPENCLAW_AGENT_REGISTERED":"RESTARTED_OPENCLAW_AGENT_RETAINED");
  run("config","validate");trace("REAL_OPENCLAW_CONTAINER_FICTION_MODEL_ONLY");
  fs.rmSync(HOME+"/state/fake-hit-"+mode+".txt",{force:true});
  const provider=fork(process.execPath,[fake]);
  await ready("http://127.0.0.1:19042/v1/models",provider);
  trace("REAL_OPENCLAW_CONTAINER_FAKE_PROVIDER_LOOPBACK");
  const gateway=fork(process.execPath,[entry,"gateway","run","--port","18991",
    "--bind","loopback","--auth","token","--token",env.OPENCLAW_GATEWAY_TOKEN]);
  await ready("http://127.0.0.1:18991/healthz",gateway);
  trace("REAL_OPENCLAW_CONTAINER_GATEWAY_READY");
  run("gateway","health","--port","18991","--token",env.OPENCLAW_GATEWAY_TOKEN);
  const bad=spawnSync(process.execPath,[entry,"gateway","health","--port","18991",
    "--token","INCORRECT-FICTIONAL-TOKEN"],{cwd:SRC,env,timeout:60000,encoding:"utf8"});
  assert.notEqual(bad.status,0);trace("REAL_OPENCLAW_CONTAINER_BAD_TOKEN_REJECTED");
  const roster=JSON.parse(run("gateway","call","agents.list","--port","18991",
    "--token",env.OPENCLAW_GATEWAY_TOKEN,"--json"));
  assert(roster.agents.some(a=>a.id==="ci-contained"));
  trace("REAL_OPENCLAW_CONTAINER_GATEWAY_AGENT_VISIBLE");
  const reply=JSON.parse(run("agent","--agent","ci-contained",
    "--message","FULL_CONTAINER_PING_20261117","--json","--timeout","90"));
  const texts=reply.result?.payloads??[];
  assert.equal(reply.status,"ok");
  assert(texts.some(x=>x.text===TRUE_RESPONSE),"Agent returned a different answer");
  assert.equal(fs.readFileSync(HOME+"/state/fake-hit-"+mode+".txt","utf8"),
    "FICTION_PROVIDER_RECEIVED_"+mode+"\n");
  trace(mode==="first"?"FIRST_CONTAINER_FAKE_AGENT_TURN":"RESTARTED_CONTAINER_FAKE_AGENT_TURN");
  trace("REAL_OPENCLAW_FULL_CONTAINER_FAKE_TURN");
  console.log("SYNTHETIC_ONLY; NO_REAL_PROVIDER; NO_OUTSIDE_NETWORK; PRODUCTION_NO_GO");
}finally{
  exitChildren();
}
