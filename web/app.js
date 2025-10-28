const api = document.querySelector('meta[name="api-base"]').content;
const out = document.getElementById('out');
const log = (x) => out.textContent = (typeof x === 'string') ? x : JSON.stringify(x, null, 2);

let sessionId = null;
let idKey = null;
let selfieKey = null;

// helper for file upload
async function uploadFile(file) {
  const res = await fetch(`${api}/presign-id`, { method: 'POST' });
  const j = await res.json();
  await fetch(j.putUrl, { method: 'PUT', headers: { 'Content-Type': file.type || 'image/jpeg' }, body: file });
  return j.key;
}

document.getElementById('btn-ping').onclick = async () => {
  log('Calling /ping...');
  const r = await fetch(`${api}/ping`);
  log(await r.text());
};

document.getElementById('btn-upload-id').onclick = async () => {
  const file = document.getElementById('file-id').files[0];
  if (!file) return log('Pick an ID photo.');
  log('Uploading ID photo...');
  idKey = await uploadFile(file);
  document.getElementById('idKey').value = idKey;
  log({ idKey });
};

document.getElementById('btn-upload-selfie').onclick = async () => {
  const file = document.getElementById('file-selfie').files[0];
  if (!file) return log('Pick a selfie.');
  log('Uploading selfie...');
  selfieKey = await uploadFile(file);
  document.getElementById('selfieKey').value = selfieKey;
  log({ selfieKey });
};

document.getElementById('btn-liveness-start').onclick = async () => {
  log('Starting liveness session...');
  const r = await fetch(`${api}/liveness/start`, { method: 'POST' });
  const j = await r.json();
  sessionId = j.sessionId;
  log(j);
};

document.getElementById('btn-liveness-result').onclick = async () => {
  if (!sessionId) return log('Start session first.');
  const r = await fetch(`${api}/liveness/results`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ sessionId })
  });
  log(await r.json());
};

document.getElementById('btn-kyc').onclick = async () => {
  if (!sessionId) return log('Start session first.');
  const idKeyInput = document.getElementById('idKey').value;
  const selfieKeyInput = document.getElementById('selfieKey').value;
  if (!idKeyInput || !selfieKeyInput) return log('Upload both ID and selfie first.');
  log('Submitting KYC...');
  const r = await fetch(`${api}/kyc/submit`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      sessionId,
      idUrl: idKeyInput,
      selfieUrl: selfieKeyInput
    })
  });
  log(await r.json());
};
