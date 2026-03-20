// ─── FLASH MESSAGES ───────────────────────────────────────────────────────
document.querySelectorAll('.flash').forEach(el => {
  el.addEventListener('click', () => el.remove());
  setTimeout(() => el.remove(), 4000);
});

// ─── MODALS ───────────────────────────────────────────────────────────────
function openModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) { overlay.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) { overlay.classList.remove('open'); document.body.style.overflow = ''; }
}
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(overlay.id); });
});

// ─── ACTIVE NAV ───────────────────────────────────────────────────────────
const path = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(item => {
  const href = item.getAttribute('href') || '';
  if (href && path.includes(href.split('/').pop())) {
    item.classList.add('active');
  }
});

// ─── PRESENÇA BUTTONS ─────────────────────────────────────────────────────
document.querySelectorAll('.presenca-options').forEach(group => {
  group.querySelectorAll('.presenca-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      group.querySelectorAll('.presenca-btn').forEach(b => b.classList.remove('ativo'));
      btn.classList.add('ativo');
      const alunoId = group.dataset.aluno;
      const status = btn.dataset.status;
      // Atualizar inputs hidden
      const hiddenPresente = document.getElementById('pres-' + alunoId);
      const hiddenJustificado = document.getElementById('just-' + alunoId);
      if (hiddenPresente) hiddenPresente.checked = (status === 'presente');
      if (hiddenJustificado) hiddenJustificado.checked = (status === 'justificada');
    });
  });
});

// ─── FILE DROP ────────────────────────────────────────────────────────────
document.querySelectorAll('.file-drop').forEach(zone => {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const input = zone.querySelector('input[type="file"]');
    if (input && e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      const label = zone.querySelector('p');
      if (label) label.textContent = e.dataTransfer.files[0].name;
    }
  });
  const input = zone.querySelector('input[type="file"]');
  if (input) {
    input.addEventListener('change', () => {
      const label = zone.querySelector('p');
      if (label && input.files.length) label.innerHTML = `<strong>${input.files[0].name}</strong> selecionado`;
    });
  }
});

// ─── FORM SUBMIT LOADER ───────────────────────────────────────────────────
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function() {
    const btn = form.querySelector('button[type="submit"]');
    if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  });
});

// ─── PROGRESS BARS ANIMATE ────────────────────────────────────────────────
function animateProgressBars() {
  document.querySelectorAll('.progress-fill[data-width]').forEach(bar => {
    setTimeout(() => { bar.style.width = bar.dataset.width + '%'; }, 200);
  });
}
document.addEventListener('DOMContentLoaded', animateProgressBars);

// ─── TURMA SELECTOR ───────────────────────────────────────────────────────
document.querySelectorAll('.turma-chip').forEach(chip => {
  chip.addEventListener('click', function(e) {
    document.querySelectorAll('.turma-chip').forEach(c => c.classList.remove('active'));
    this.classList.add('active');
  });
});
