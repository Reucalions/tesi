// Fixture di trasporto: API SaaS reali, identita e Fabric simulati, solo loopback.
// Non usare questo processo per un deployment o per misurare il reasoner reale.
const path = require("node:path");
const fs = require("node:fs");
const backend = process.env.SAAS_TEST_BACKEND;
const state = process.env.SAAS_TEST_STATE;
if (!backend || !state) throw new Error("Explicit isolated backend and state directories required");
const load = file => require(path.join(backend, file));
const NetworkPool = load("dist/NetworkPool.js").default;
const Authorization = load("dist/Authorization.js").default;
const IdentityCache = load("dist/IdentityCache.js").default;
const config = load("dist/config.js").default;
const { SaaSServiceAdapter } = load("dist/services/SaaSServiceAdapter.js");
const FabricCA = load("node_modules/fabric-ca-client");
const encode = value => Buffer.from(JSON.stringify(value));
const ledgerFile=path.join(state,'fabric-state.json');
const saved=fs.existsSync(ledgerFile)?JSON.parse(fs.readFileSync(ledgerFile,'utf8')):{graphs:[],recommendations:[],commits:[]};
const graphs = new Map(saved.graphs);
const recommendations=new Map(saved.recommendations);
const commits=new Map(saved.commits);
const persistLedger=()=>fs.writeFileSync(ledgerFile,JSON.stringify({graphs:[...graphs],recommendations:[...recommendations],commits:[...commits]}));
const calls = [];
SaaSServiceAdapter.setStorageDir(path.join(state, "decisions"));
if (process.env.SAAS_TEST_SNAPSHOT_ID) {
  // Explicit fixture alias; this does not attest deployment of the generated ALN.
  SaaSServiceAdapter.registerKnowledgeSnapshot({ ...SaaSServiceAdapter.getActiveKnowledgeSnapshot(),
    snapshotId: process.env.SAAS_TEST_SNAPSHOT_ID });
}
FabricCA.prototype.enroll = async () => ({ key: "fixture-key", certificate: "fixture-certificate" });
IdentityCache.put = async () => "fixture-token";
Authorization.getFromToken = async () => ({ identity: { mspId: "Org1MSP" }, user: { getName: () => "fixture" } });

function binding(channel, chaincode, expected) {
  if (channel !== config.CHANNEL_NAME || chaincode !== expected) throw new Error("Wrong Fabric binding");
}
NetworkPool.invoke = async (_identity, channel, chaincode, method, args) => {
  binding(channel, chaincode, config.ARGUMENTATION_CHAINCODE);
  calls.push({ method, args, chaincode });
  if (method === "StoreGraph") graphs.set(args[0], JSON.parse(args[1]));
  else if (method === 'StoreRecommendation') {
    const helpers=load('dist/services/FinalizationValidation.js');
    const doc=helpers.validateFinalizationDocument(args[0]);
    const id=helpers.finalizationIdentity(doc);
    const original=recommendations.get(id);
    if(original){
      if(original.document_json!==args[0] || original.provenance_json!==args[1]) throw new Error('FINALIZATION_CONFLICT');
      return encode(original);
    }
    const tx='fixture-tx-'+id;
    const record={contract:'shared-finalization-record-v1',finalization_id:id,tenant_id:doc.tenant_id,
      document_json:args[0],document_sha256:helpers.rawDigest(args[0]),provenance_json:args[1],
      provenance_sha256:helpers.rawDigest(args[1]),transaction_id:tx};
    recommendations.set(id,record);
    commits.set(tx,{transaction_id:tx,block_number:String(commits.size+1),validation_code:0,successful:true});
    persistLedger();
    const result=encode(record);result.commitReceipt=commits.get(tx);return result;
  }
  else if (method !== "RankGraph") throw new Error("Unexpected invoke");
  const tx='fixture-rank-tx-'+String(commits.size+1);
  const receipt={transaction_id:tx,block_number:String(commits.size+1),validation_code:0,successful:true};
  commits.set(tx,receipt);persistLedger();
  const result=encode({success:'OK'});result.commitReceipt=receipt;return result;
};
NetworkPool.query = async (_identity, channel, chaincode, method, args) => {
  calls.push({ method, args, chaincode });
  if(method==='ReadRecommendation') {
    binding(channel,chaincode,config.ARGUMENTATION_CHAINCODE);
    return encode({record:recommendations.get(args[0])??null});
  }
  if (method === "Get") {
    binding(channel, chaincode, config.ARGUMENTATION_CHAINCODE);
    if (graphs.has(args[0])) return encode({ success: JSON.stringify(graphs.get(args[0])) });
    const graph = graphs.get(args[0].replace(/_rank$/, ""));
    if (!graph) return encode({ error: "NOT_FOUND" });
    const rows = graph.nodes.filter(node => node.type === "strategy").map(node => ({
      name: node.id, score: node.id === "S_PATCH" ? 0.9 : 0.8,
    }));
    if (rows.some(row => row.name === "S_BROKEN")) delete rows[0].score;
    return encode({ success: JSON.stringify(rows) });
  }
  binding(channel, chaincode, config.SEMANTIC_CHAINCODE);
  if (method !== "ExplainAffinity" || args.length !== 3 || args[0] !== "fixture-tbox") {
    throw new Error("Incorrect ExplainAffinity binding");
  }
  const [, resourceIRI, requestIRI] = args;
  const requestName = requestIRI.split(":").pop();
  if (requestName === "cm-timeout") throw new Error("Simulated peer timeout");
  if (requestName === "cm-malformed") return encode({ score: 100 });
  const native = {
    resourceIRI, score: 100, abductionPenalty: 0, contractionPenalty: 0,
    topPenalty: 0, hypothesis: "Hypothesis: Thing\nPenalty: 0.00", giveUp: "", keep: "",
  };
  if (requestName === "cm-needs") Object.assign(native, {
    score: 99, abductionPenalty: 1, hypothesis: "Hypothesis: Request\nPenalty: 1.00",
  });
  if (requestName === "cm-conflict") Object.assign(native, {
    score: 98, contractionPenalty: 2, hypothesis: "", giveUp: "Give up: conflict",
  });
  return encode(native);
};
NetworkPool.getCommitStatus=async(_identity,channel,tx)=>{
  if(channel!==config.CHANNEL_NAME || !commits.has(tx)) throw new Error('Unknown fixture commit');
  calls.push({method:'getCommitStatus',transaction_id:tx,channel});return commits.get(tx);
};
const { app } = load("dist/index.js");
const server = app.listen(0, "127.0.0.1", () => {
  fs.writeFileSync(path.join(state, "ready.json"), JSON.stringify({ url: `http://127.0.0.1:${server.address().port}` }));
});
process.on("SIGTERM", () => {
  fs.writeFileSync(path.join(state, "fabric-calls.json"), JSON.stringify(calls, null, 2));
  server.close(() => process.exit(0));
});
