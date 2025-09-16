const form = document.getElementById('input-form');
const input = document.getElementById('input');
const messages = document.getElementById('messages');

form.addEventListener('submit', e => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    appendMessage('user', text);
    input.value = '';
    // TODO: send text to backend and append response
});

function appendMessage(sender, text) {
    const div = document.createElement('div');
    div.className = 'message';
    div.innerHTML = `<strong>${sender}:</strong> ${escapeHtml(text)}`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(str) {
    return str.replace(/[&<>"']/g, m => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
}