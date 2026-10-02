(() => {
  const messages = [
    'You do not need the whole map today. One thoughtful next step is enough.',
    'Your path is yours to build. Let’s make the next step a little clearer.',
    'Big careers grow from small, steady steps. You’re in the right place to begin.',
    'You already have a starting point: the goals you care about. We can build from there.',
    'Progress is not always a leap. Sometimes it is simply showing up again today.'
  ];
  const message = document.querySelector('[data-guide-message]');
  if (!message) return;
  message.textContent = messages[Math.floor(Math.random() * messages.length)];
})();
