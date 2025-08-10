// Theme toggle with persistence
(function setupThemeToggle() {
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const saved = localStorage.getItem('theme');
  const isDark = saved ? saved === 'dark' : prefersDark;
  if (isDark) document.body.classList.add('dark');

  const toggleBtn = document.querySelector('.theme-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      document.body.classList.toggle('dark');
      const nowDark = document.body.classList.contains('dark');
      localStorage.setItem('theme', nowDark ? 'dark' : 'light');
    });
  }
})();

// Simple client-side search for index cards
(function setupSearch() {
  const input = document.getElementById('search');
  if (!input) return; // present only on index

  const cards = Array.from(document.querySelectorAll('.card'));

  function normalize(text) {
    return (text || '')
      .toString()
      .toLowerCase()
      .replace(/[ё]/g, 'е')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function getCardText(card) {
    const name = card.getAttribute('data-name') || '';
    const tags = card.getAttribute('data-tags') || '';
    const paragraph = card.querySelector('.card-content p');
    return `${name} ${tags} ${paragraph ? paragraph.textContent : ''}`;
  }

  const cardIndex = cards.map(card => ({
    card,
    text: normalize(getCardText(card))
  }));

  function applyFilter(query) {
    const q = normalize(query);
    if (!q) {
      cards.forEach(c => c.style.display = 'flex');
      return;
    }
    cardIndex.forEach(({ card, text }) => {
      card.style.display = text.includes(q) ? 'flex' : 'none';
    });
  }

  input.addEventListener('input', (e) => applyFilter(e.target.value));
})();


