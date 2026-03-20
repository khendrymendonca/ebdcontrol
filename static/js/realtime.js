// Supabase Realtime — atualizações ao vivo
// Este script é injetado nos dashboards e lê as variáveis do template

const SUPABASE_URL = window.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || '';

if (SUPABASE_URL && SUPABASE_ANON_KEY) {
    const { createClient } = supabase;
    const sb = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    // ── Ranking e notas ao vivo ────────────────────────────────────────────
    sb.channel('logos-notas')
        .on('postgres_changes', {
            event: '*', schema: 'public', table: 'respostas_prova'
        }, payload => {
            console.log('[Realtime] Nota atualizada:', payload);
            if (window.onNotaUpdate) window.onNotaUpdate(payload);
            showRealtimePulse('Notas atualizadas!');
        })
        .subscribe();

    // ── Presença ao vivo ───────────────────────────────────────────────────
    sb.channel('logos-presencas')
        .on('postgres_changes', {
            event: '*', schema: 'public', table: 'presencas'
        }, payload => {
            console.log('[Realtime] Presença atualizada:', payload);
            if (window.onPresencaUpdate) window.onPresencaUpdate(payload);
        })
        .subscribe();

    // ── Entregas de trabalho ao vivo ────────────────────────────────────────
    sb.channel('logos-entregas')
        .on('postgres_changes', {
            event: 'INSERT', schema: 'public', table: 'entregas_trabalho'
        }, payload => {
            console.log('[Realtime] Nova entrega:', payload);
            showRealtimePulse('Nova entrega recebida!');
            const counter = document.getElementById('trabalhos-pendentes-count');
            if (counter) counter.textContent = parseInt(counter.textContent || '0') + 1;
        })
        .subscribe();
}

function showRealtimePulse(msg) {
    const dot = document.getElementById('realtime-status');
    if (dot) {
        dot.dataset.tooltip = msg;
        dot.style.background = '#00E676';
        dot.style.transform = 'scale(1.5)';
        setTimeout(() => { dot.style.transform = 'scale(1)'; }, 600);
    }
    // Toast
    const container = document.querySelector('.flash-container');
    if (container) {
        const toast = document.createElement('div');
        toast.className = 'flash flash-info';
        toast.textContent = '⚡ ' + msg;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}
