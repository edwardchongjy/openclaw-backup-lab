import fs from "node:fs";
import http from "node:http";
const expected="FULL_CONTAINER_PING_20261117";
const response="FULL_CONTAINER_FAKE_REPLY_20261117";
const json=(res,data)=>{
  const raw=JSON.stringify(data);
  res.writeHead(200,{"content-type":"application/json","content-length":Buffer.byteLength(raw)});
  res.end(raw);
};
http.createServer(async(req,res)=>{
  if(req.method==="GET"&&req.url==="/v1/models"){
    return json(res,{object:"list",data:[{id:"fake-echo",object:"model",owned_by:"ci-fake"}]});
  }
  if(req.method!=="POST"||req.url!=="/v1/chat/completions"){
    res.writeHead(404);res.end();return;
  }
  const parts=[];let total=0;
  for await(const part of req){total+=part.length;if(total>2000000)break;parts.push(part);}
  if(total>2000000){res.writeHead(413);res.end();return;}
  let doc;
  try{doc=JSON.parse(Buffer.concat(parts).toString("utf8"))}catch{res.writeHead(400);res.end();return}
  if(doc.model!=="fake-echo"||!JSON.stringify(doc).includes(expected)){
    res.writeHead(422);res.end();return;
  }
  fs.writeFileSync("/home/ci/state/fake-hit-"+process.env.CI_PILOT_MODE+".txt","FICTION_PROVIDER_RECEIVED_"+process.env.CI_PILOT_MODE+"\n");
  const chunks=[
    {id:"ci-real-container",object:"chat.completion.chunk",created:1,model:"fake-echo",choices:[{index:0,delta:{role:"assistant",content:response},finish_reason:null}]},
    {id:"ci-real-container",object:"chat.completion.chunk",created:1,model:"fake-echo",choices:[{index:0,delta:{},finish_reason:"stop"}]}
  ];
  const raw=chunks.map(x=>"data: "+JSON.stringify(x)+"\n\n").join("")+"data: [DONE]\n\n";
  res.writeHead(200,{"content-type":"text/event-stream","content-length":Buffer.byteLength(raw)});
  res.end(raw);
}).listen(19042,"127.0.0.1");
