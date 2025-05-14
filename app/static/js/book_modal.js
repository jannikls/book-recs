// Standardized Book Info Modal
(function() {
  // Create modal HTML if not present
  if (!document.getElementById('book-modal')) {
    const modal = document.createElement('div');
    modal.id = 'book-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div id="book-modal-backdrop" style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:#0008;z-index:1000;display:flex;align-items:center;justify-content:center;">
        <div id="book-modal-content" style="background:#fff;padding:2em 2em 1.5em 2em;border-radius:12px;max-width:480px;width:90vw;box-shadow:0 8px 32px #0003;position:relative;font-family:'Inter',Arial,sans-serif;">
          <button id="book-modal-close" style="position:absolute;top:12px;right:16px;font-size:1.2em;background:none;border:none;cursor:pointer;">&times;</button>
          <div id="book-modal-body"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    document.getElementById('book-modal-close').onclick = hideBookModal;
    document.getElementById('book-modal-backdrop').onclick = function(e) {
      if (e.target === this) hideBookModal();
    };
  }

  window.showBookModal = function(book) {
    const body = document.getElementById('book-modal-body');
    body.innerHTML = `
      <div style="text-align:center;margin-bottom:1em;">
        <img src="${book.cover_url || 'https://via.placeholder.com/96x144?text=No+Cover'}" alt="Cover" style="width:96px;height:144px;object-fit:cover;border-radius:6px;background:#eee;box-shadow:0 2px 8px #0001;" onerror="this.src='https://via.placeholder.com/96x144?text=No+Cover'" />
      </div>
      <div style="font-size:1.2em;font-weight:600;text-align:center;">${book.title}</div>
      <div style="color:#555;text-align:center;margin-bottom:0.6em;">${book.author || ''}</div>
      <div style="background:#ff9800;color:#fff;display:inline-block;padding:2px 10px;border-radius:10px;font-size:0.97em;margin-bottom:0.5em;">Niche Score: ${book.niche_score || '?'}</div>
      ${book.description ? `<div style='margin:1em 0 0.7em 0;color:#222;line-height:1.6;font-size:1.03em;'>${book.description}</div>` : ''}
      <div style='color:#888;font-size:0.97em;margin-top:0.7em;'>Book ID: ${book.book_id || ''}</div>
    `;
    document.getElementById('book-modal').style.display = 'block';
  };

  window.hideBookModal = function() {
    document.getElementById('book-modal').style.display = 'none';
  };
})();
