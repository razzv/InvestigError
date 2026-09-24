const $ = (id) => document.getElementById(id);
let source = null;
let report = null;
let reportMarkdown = '';
let previewReady = false;

function node(tag, content, className) {
  const element = document.createElement(tag);
  if (content !== undefined) element.textContent = String(content);
  if (className) element.className = className;
  return element;
}

function status(message) { $('status').textContent = message; }
function error(message) { $('error').textContent = message; $('error').hidden = false; }
function clearError() { $('error').textContent = ''; $('error').hidden = true; }
function busy(value) {
  for (const id of ['example', 'upload', 'validate', 'analyze', 'consent', 'explain']) $(id).disabled = value;
  if (!value) refreshButtons();
}
function refreshButtons() {
  $('validate').disabled = !source;
  $('analyze').disabled = !source;
  $('consent').disabled = !previewReady;
  $('explain').disabled = !previewReady || !$('consent').checked;
}
function resetForSource(file) {
  source = file;
  report = null;
  reportMarkdown = '';
  previewReady = false;
  $('consent').checked = false;
  $('preview').textContent = 'Validate the bundle to see selected provider context.';
  $('sanitized').textContent = 'Validate the bundle to see sanitized input.';
  $('coverage').textContent = 'No provider context selected.';
  $('report').hidden = true;
  $('empty').hidden = false;
  $('json-export').disabled = true;
  $('md-export').disabled = true;
  clearError();
  status(file ? `Loaded ${file.name}. Validate it or run rules.` : 'Choose a synthetic example or upload a JSON/JSONL bundle.');
  refreshButtons();
}
async function request(path, allowCloud = false) {
  if (!source) return null;
  clearError();
  busy(true);
  status('Working locally…');
  try {
    const format = source.name.toLowerCase().endsWith('.jsonl') ? 'jsonl' : 'json';
    const headers = { 'X-Incident-Format': format, 'Content-Type': 'application/octet-stream' };
    if (allowCloud) headers['X-Allow-Cloud'] = 'true';
    const response = await fetch(path, { method: 'POST', body: source, headers });
    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return data;
  } catch (failure) {
    error(failure.message || 'Request failed.');
    status('Review the error and try again.');
    return null;
  } finally { busy(false); }
}

function evidenceLink(id) {
  const button = node('button', id, 'evidence-link');
  button.type = 'button';
  button.addEventListener('click', () => selectEvidence(id));
  return button;
}
function addReferences(container, ids) {
  if (!ids.length) { container.append(node('span', 'No evidence cited.')); return; }
  ids.forEach((id, index) => {
    if (index) container.append(node('span', ', '));
    container.append(evidenceLink(id));
  });
}
function selectEvidence(id) {
  const record = report?.evidence.find((item) => item.id === id);
  if (!record) return;
  $('evidence').textContent = JSON.stringify(record, null, 2);
  document.querySelectorAll('.timeline-item').forEach((item) => {
    item.classList.toggle('selected', item.dataset.evidenceId === id);
  });
  $('evidence').focus();
  $('evidence').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function addList(target, values) {
  target.replaceChildren();
  for (const value of values) target.append(node('li', value));
}
function renderReport(data) {
  report = data.report;
  reportMarkdown = data.markdown;
  $('empty').hidden = true;
  $('report').hidden = false;
  $('json-export').disabled = false;
  $('md-export').disabled = false;
  $('report-meta').textContent = `${report.title} · ${report.evidence.length} records · AI: ${report.ai_status}`;
  $('findings').replaceChildren();
  for (const finding of report.findings) {
    const card = node('article', undefined, `finding ${finding.severity}`);
    card.append(node('strong', `${finding.rule_id} · ${finding.severity.toUpperCase()}`), node('p', finding.statement));
    const refs = node('div'); refs.append(node('span', 'Evidence: ')); addReferences(refs, finding.evidence_ids); card.append(refs);
    for (const limit of finding.limitations) card.append(node('p', `Limitation: ${limit}`, 'hint'));
    for (const check of finding.next_checks) card.append(node('p', `Next check: ${check}`, 'hint'));
    $('findings').append(card);
  }
  if (!report.findings.length) $('findings').append(node('p', 'No rule findings.'));
  addList($('limitations'), report.evidence_limitations);
  $('ai').replaceChildren();
  if (report.ai_explanation) {
    $('ai').append(node('p', report.ai_explanation.summary));
    for (const item of report.ai_explanation.hypotheses) {
      const card = node('article', undefined, 'hypothesis');
      card.append(node('strong', `Hypothesis · ${item.category}`), node('p', item.statement));
      const refs = node('div'); refs.append(node('span', 'Evidence: ')); addReferences(refs, item.evidence_ids); card.append(refs);
      card.append(node('p', `Reasoning: ${item.reasoning_summary}`, 'hint'));
      for (const missing of item.missing_evidence) card.append(node('p', `Missing evidence: ${missing}`, 'hint'));
      for (const step of item.verification_steps) card.append(node('p', `Verify: ${step}`, 'hint'));
      $('ai').append(card);
    }
    if (report.ai_explanation.alternatives.length) {
      $('ai').append(node('h4', 'Alternatives'));
      for (const item of report.ai_explanation.alternatives) {
        const row = node('p', item.statement + ' · Evidence: ');
        addReferences(row, item.evidence_ids); $('ai').append(row);
        for (const missing of item.missing_evidence) $('ai').append(node('p', `Missing evidence: ${missing}`, 'hint'));
      }
    }
    if (report.ai_explanation.next_steps.length) {
      $('ai').append(node('h4', 'Next steps'));
      const list = node('ol'); for (const step of report.ai_explanation.next_steps) list.append(node('li', step)); $('ai').append(list);
    }
    for (const limit of report.ai_explanation.limitations) $('ai').append(node('p', `AI limitation: ${limit}`, 'hint'));
  } else {
    $('ai').append(node('p', report.ai_status === 'not_requested' ? 'AI is off. Rules ran locally.' : `AI ${report.ai_status}. The rules report remains available.`, 'hint'));
  }
  for (const warning of report.metadata.warnings) $('ai').append(node('p', warning, 'hint'));
  $('timeline').replaceChildren();
  for (const item of report.timeline) {
    const record = report.evidence.find((entry) => entry.id === item.evidence_id);
    const row = node('li', undefined, 'timeline-item'); row.dataset.evidenceId = item.evidence_id;
    row.append(node('span', `${item.occurred_at_utc} · ${record.kind} · `), evidenceLink(record.id), node('span', ` · ${record.message}`));
    $('timeline').append(row);
  }
  $('evidence').textContent = 'Select an evidence link.';
  status(`Report ready: ${report.findings.length} finding(s), ${report.evidence.length} evidence records.`);
}
function download(extension, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = node('a');
  link.href = url;
  link.download = `investigerror-${report.incident_id}.${extension}`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$('example').addEventListener('change', async (event) => {
  const id = event.target.value;
  if (!id) { resetForSource(null); return; }
  clearError(); busy(true);
  try {
    const response = await fetch(`/api/examples/${encodeURIComponent(id)}`);
    if (!response.ok) throw new Error('Example could not be loaded.');
    const blob = await response.blob();
    resetForSource(new File([blob], `${id}.${id.endsWith('-jsonl') ? 'jsonl' : 'json'}`));
    $('upload').value = '';
  } catch (failure) { resetForSource(null); error(failure.message); }
  finally { busy(false); }
});
$('upload').addEventListener('change', (event) => { $('example').value = ''; resetForSource(event.target.files[0] || null); });
$('validate').addEventListener('click', async () => {
  const data = await request('/api/validate');
  if (!data) return;
  $('sanitized').textContent = JSON.stringify(data.bundle, null, 2);
  $('preview').textContent = data.provider_context ? JSON.stringify(data.provider_context, null, 2) : data.preview_error;
  const meta = data.provider_context?.metadata;
  $('coverage').textContent = meta ? `${meta.selected_record_count} selected, ${meta.omitted_record_count} omitted. Only the selected context below is sent.` : 'Provider context could not be prepared; narrow the bundle.';
  previewReady = Boolean(data.provider_context);
  $('consent').checked = false;
  refreshButtons();
  status(`Valid bundle: ${data.bundle.records.length} records. Review sanitized input and provider context.`);
});
$('analyze').addEventListener('click', async () => { const data = await request('/api/analyze'); if (data) renderReport(data); });
$('consent').addEventListener('change', refreshButtons);
$('explain').addEventListener('click', async () => {
  if (!previewReady || !$('consent').checked) return;
  const data = await request('/api/explain', true);
  $('consent').checked = false;
  refreshButtons();
  if (data) renderReport(data);
});
$('json-export').addEventListener('click', () => { if (report) download('json', JSON.stringify(report, null, 2) + '\n', 'application/json'); });
$('md-export').addEventListener('click', () => { if (report) download('md', reportMarkdown, 'text/markdown'); });

fetch('/api/examples').then((response) => response.json()).then((items) => {
  for (const item of items) { const option = node('option', item.filename); option.value = item.id; $('example').append(option); }
}).catch(() => error('Bundled examples could not be listed. Upload is still available.'));
