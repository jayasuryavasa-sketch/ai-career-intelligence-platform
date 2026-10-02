/* Single API boundary: configure CAREER_API_URL before deploying the static frontend. */
(() => {
  const configured = window.CAREER_API_URL || localStorage.getItem('career_api_url') || 'http://127.0.0.1:5000/api';
  window.api = async (path, options = {}) => {
    const { timeoutMs = 45000, ...fetchOptions } = options;
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const csrf = window.careerCsrfToken && !['GET','HEAD','OPTIONS'].includes((fetchOptions.method || 'GET').toUpperCase()) ? { 'X-CSRF-Token': window.careerCsrfToken } : {};
      const response = await fetch(`${configured}${path}`, { credentials: 'include', ...fetchOptions, signal: controller.signal, headers: { ...(fetchOptions.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...csrf, ...(fetchOptions.headers || {}) } });
      let data = {}; try { data = await response.json(); } catch (_) {}
      if (!response.ok) { const err = new Error(data.error?.message || 'The request could not be completed. Please try again.'); err.status = response.status; err.code = data.error?.code; throw err; }
      return data;
    } catch (err) { if (err.name === 'AbortError') throw new Error('This is taking longer than expected. Please try again.'); if (err instanceof TypeError) throw new Error('The career server is unavailable. Check that the backend is running and try again.'); throw err; }
    finally { clearTimeout(timer); }
  };
  window.escapeHTML = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
})();
