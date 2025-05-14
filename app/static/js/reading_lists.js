// Fetch and render all saved reading lists, and show as clickable cards
async function fetchLists() {
  const resp = await fetch('/api/reading-lists');
  if (!resp.ok) return [];
  return await resp.json();
}

function renderLists(lists) {
  const ul = document.getElementById('lists');
  ul.innerHTML = '';
  lists.forEach(list => {
    const li = document.createElement('li');
    li.className = 'reading-list-card';
    li.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <a href="/reading-lists/${list.id}" style="font-weight:600;font-size:1.12em;">${list.name}</a>
          <span style="color:#888;font-size:0.95em;">(${list.url})</span><br>
          <span style="color:#999;font-size:0.95em;">Last fetched: ${list.last_fetched||'never'}</span>
        </div>
        <button class="view-list-btn" data-list='${JSON.stringify(list)}' style="margin-left:1em;">View</button>
      </div>
    `;
    // Modal on card or button click
    li.onclick = function(e) {
      if (e.target.classList.contains('view-list-btn')) {
        const list = JSON.parse(e.target.getAttribute('data-list'));
        showReadingListModal(list);
        e.stopPropagation();
        return;
      }
      // Card click: go to list
      window.location.href = `/reading-lists/${list.id}`;
    };
    ul.appendChild(li);
  });
}

// Standardized modal for reading list info
window.showReadingListModal = function(list) {
  if (!document.getElementById('reading-list-modal')) {
    const modal = document.createElement('div');
    modal.id = 'reading-list-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div id="reading-list-modal-backdrop" style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:#0008;z-index:1000;display:flex;align-items:center;justify-content:center;">
        <div id="reading-list-modal-content" style="background:#fff;padding:2em 2em 1.5em 2em;border-radius:12px;max-width:420px;width:90vw;box-shadow:0 8px 32px #0003;position:relative;font-family:'Inter',Arial,sans-serif;">
          <button id="reading-list-modal-close" style="position:absolute;top:12px;right:16px;font-size:1.2em;background:none;border:none;cursor:pointer;">&times;</button>
          <div id="reading-list-modal-body"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    document.getElementById('reading-list-modal-close').onclick = hideReadingListModal;
    document.getElementById('reading-list-modal-backdrop').onclick = function(e) {
      if (e.target === this) hideReadingListModal();
    };
  }
  const body = document.getElementById('reading-list-modal-body');
  body.innerHTML = `
    <div style="font-size:1.2em;font-weight:600;text-align:center;margin-bottom:0.6em;">${list.name}</div>
    <div style="text-align:center;margin-bottom:1em;">
      <a href="${list.url}" target="_blank">${list.url}</a>
    </div>
    <div style="color:#999;text-align:center;margin-bottom:1.2em;">Last fetched: ${list.last_fetched||'never'}</div>
    <div style="text-align:center;"><a href="/reading-lists/${list.id}" class="add-btn">Open List</a></div>
  `;
  document.getElementById('reading-list-modal').style.display = 'block';
};
window.hideReadingListModal = function() {
  document.getElementById('reading-list-modal').style.display = 'none';
};

document.getElementById('import-form').onsubmit = async function(e) {
  e.preventDefault();
  const form = e.target;
  const data = {
    name: form.name.value,
    url: form.url.value
  };
  const resp = await fetch('/reading-lists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (resp.ok) {
    form.reset();
    fetchLists().then(renderLists);
  } else {
    alert('Failed to import list!');
  }
};

window.onload = () => {
  fetchLists().then(renderLists);
};
