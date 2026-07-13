const state = { projects: [], expanded: new Set(), loading: new Set() };
const list = document.querySelector('#projectList');
const count = document.querySelector('#projectCount');
const notice = document.querySelector('#notice');
const refreshButton = document.querySelector('#refreshButton');

const projectColors = ['#2f6b4f', '#315f89', '#785c92', '#9a5b3d'];

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.hidden = !message;
  notice.classList.toggle('error', isError);
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function isolationLabel(value) {
  return {
    namespace: '独立数据',
    'frontend-only': '仅前端',
    shared: '共享数据',
  }[value] || '独立数据';
}

function formatTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date);
}

async function preview(project, branch) {
  const key = `${project.id}:${branch.name}`;
  if (branch.preview?.url) {
    window.location.assign(branch.preview.url);
    return;
  }
  state.loading.add(key);
  render();
  showNotice('');
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}/branches/${encodeURIComponent(branch.name)}/start`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || '预览启动失败');
    window.location.assign(payload.preview.url);
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    state.loading.delete(key);
    render();
  }
}

async function stopPreview(project, branch) {
  const key = `${project.id}:${branch.name}:stop`;
  state.loading.add(key);
  render();
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}/branches/${encodeURIComponent(branch.name)}/stop`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || '停止失败');
    await loadProjects(false);
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    state.loading.delete(key);
    render();
  }
}

function actionGroup(project, branch) {
  const wrapper = element('div', 'preview-actions');
  const key = `${project.id}:${branch.name}`;
  const busy = state.loading.has(key);
  const primary = element('button', `primary-button${branch.preview ? ' running' : ''}`, busy ? '正在启动' : branch.preview ? '打开预览' : '预览');
  primary.type = 'button';
  primary.disabled = busy || !project.available;
  primary.addEventListener('click', () => preview(project, branch));
  wrapper.append(primary);
  if (branch.preview) {
    const stopping = state.loading.has(`${key}:stop`);
    const stop = element('button', 'secondary-button stop-button', stopping ? '…' : '停止');
    stop.type = 'button';
    stop.disabled = stopping;
    stop.title = '停止这个分支的预览';
    stop.addEventListener('click', () => stopPreview(project, branch));
    wrapper.append(stop);
  }
  return wrapper;
}

function branchRow(project, branch) {
  const row = element('div', 'branch-row');
  const summary = element('div', 'branch-summary');
  summary.append(element('span', 'branch-name', branch.name));
  summary.append(element('span', 'branch-subject', branch.subject || '暂无提交摘要'));
  row.append(summary);
  const middle = element('div', 'branch-time');
  middle.append(element('span', `isolation-tag ${project.isolation || ''}`, isolationLabel(project.isolation)));
  middle.append(document.createTextNode(`  ${formatTime(branch.committedAt)}`));
  row.append(middle);
  row.append(actionGroup(project, branch));
  return row;
}

function projectView(project, index) {
  const article = element('article', `project${project.available ? '' : ' unavailable'}`);
  article.style.setProperty('--project-accent', projectColors[index % projectColors.length]);
  article.append(element('div', 'project-rail'));
  const body = element('div', 'project-body');
  const main = element('div', 'project-main');
  const copy = element('div');
  copy.append(element('p', 'project-label', project.available ? (project.dirty ? '有未提交修改' : '工作区已同步') : '项目不可用'));
  copy.append(element('h2', 'project-title', project.name));
  if (project.description) copy.append(element('p', 'project-description', project.description));
  const current = project.currentBranch;
  const meta = element('div', 'project-meta');
  if (current) {
    const branchMeta = element('span', 'meta-item');
    branchMeta.append(element('span', 'meta-label', '当前分支'));
    branchMeta.append(element('span', 'branch-name', current.name));
    meta.append(branchMeta);
    const commitMeta = element('span', 'meta-item');
    commitMeta.append(element('span', 'meta-label', '最新提交'));
    commitMeta.append(element('span', 'commit-sha', current.sha));
    meta.append(commitMeta);
    if (project.dirty) meta.append(element('span', 'meta-item dirty', '本地修改会进入当前分支预览'));
  }
  copy.append(meta);
  main.append(copy);
  if (current) main.append(actionGroup(project, current));
  body.append(main);

  const extraBranches = project.branches?.filter((branch) => !branch.current) || [];
  if (extraBranches.length) {
    const toggle = element('button', 'branch-toggle', `${extraBranches.length} 个其他活跃分支`);
    toggle.type = 'button';
    toggle.setAttribute('aria-expanded', String(state.expanded.has(project.id)));
    toggle.addEventListener('click', () => {
      state.expanded.has(project.id) ? state.expanded.delete(project.id) : state.expanded.add(project.id);
      render();
    });
    body.append(toggle);
    if (state.expanded.has(project.id)) {
      const panel = element('div', 'branch-panel');
      extraBranches.forEach((branch) => panel.append(branchRow(project, branch)));
      body.append(panel);
    }
  }
  article.append(body);
  return article;
}

function render() {
  list.replaceChildren();
  count.textContent = `${state.projects.length} 个项目`;
  if (!state.projects.length) {
    list.append(document.querySelector('#emptyTemplate').content.cloneNode(true));
    return;
  }
  state.projects.forEach((project, index) => list.append(projectView(project, index)));
}

async function loadProjects(showLoading = true) {
  if (showLoading) refreshButton.disabled = true;
  try {
    const response = await fetch('/api/projects', { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || '项目状态读取失败');
    state.projects = payload.projects || [];
    showNotice('');
    render();
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener('click', () => loadProjects());
loadProjects();
setInterval(() => loadProjects(false), 8000);
