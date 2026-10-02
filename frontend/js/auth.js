document.querySelector('#auth-form')?.addEventListener('submit', async e => {
  e.preventDefault(); const form=e.currentTarget, mode=form.dataset.mode, msg=form.querySelector('.auth-msg'), btn=form.querySelector('button[type=submit],button'); const fd=new FormData(form), v=Object.fromEntries(fd.entries()); msg.textContent=''; btn.disabled=true; btn.textContent='Securing your workspace…';
  try {
    let out;
    if(mode==='register') { if(v.password!==v.confirm) throw new Error('Passwords do not match.'); out=await api('/auth/register',{method:'POST',body:JSON.stringify(v)}); location.href='dashboard.html'; }
    if(mode==='login') { out=await api('/auth/login',{method:'POST',body:JSON.stringify(v)}); const go=new URLSearchParams(location.search).get('next'); location.href=go==='resume'?'resume-analyzer.html':'dashboard.html'; }
    if(mode==='forgot') { out=await api('/auth/forgot-password',{method:'POST',body:JSON.stringify(v)}); msg.textContent=out.delivery ? `${out.message} ${out.delivery} Token: ${out.dev_reset_token}` : out.message; }
    if(mode==='reset') { if(v.password!==v.confirm) throw new Error('Passwords do not match.'); out=await api('/auth/reset-password',{method:'POST',body:JSON.stringify({password:v.password,token:new URLSearchParams(location.search).get('token')||''})}); msg.textContent=out.message; setTimeout(()=>location.href='login.html',1600); }
  } catch(err){ msg.textContent=err.message; msg.classList.add('error'); }
  finally { btn.disabled=false; btn.textContent=mode==='login'?'Sign in ↗':mode==='register'?'Create account ↗':mode==='reset'?'Update password':'Send reset link'; }
});
