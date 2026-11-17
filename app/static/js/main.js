/* SkillGap – main JavaScript
   Vanilla JS only, no frameworks */

// ============ THEME TOGGLE ============
(function initTheme() {
  try {
    const saved = localStorage.getItem('skillgap-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  } catch (e) { /* localStorage unavailable */ }
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('skillgap-theme', next); } catch (e) {}
}

// ============ USER MENU ============
document.addEventListener('DOMContentLoaded', function() {
  const userMenu = document.querySelector('.user-menu');
  if (userMenu) {
    const btn = userMenu.querySelector('.user-menu-btn');
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      userMenu.classList.toggle('open');
    });
    document.addEventListener('click', function() {
      userMenu.classList.remove('open');
    });
  }

  // Mobile menu
  const mobileBtn = document.querySelector('.mobile-menu-btn');
  if (mobileBtn) {
    mobileBtn.addEventListener('click', function() {
      const links = document.querySelector('.nav-links');
      links.classList.toggle('mobile-open');
    });
  }
});

// ============ TABS ============
function initTabs(container) {
  const tabs = container.querySelectorAll('.tab');
  const panels = container.querySelectorAll('.tab-panel');
  
  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      const target = this.getAttribute('data-tab');
      
      tabs.forEach(function(t) { t.classList.remove('active'); });
      panels.forEach(function(p) { p.classList.remove('active'); });
      
      this.classList.add('active');
      const panel = document.getElementById('panel-' + target);
      if (panel) panel.classList.add('active');
    });
  });
}

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.tabs-container').forEach(initTabs);
});

// ============ FILE UPLOAD ============
function initUploadZone(zoneId, inputId, infoId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const info = document.getElementById(infoId);
  if (!zone || !input) return;

  zone.addEventListener('click', function() { input.click(); });
  
  zone.addEventListener('dragover', function(e) {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  
  zone.addEventListener('dragleave', function() {
    zone.classList.remove('dragover');
  });
  
  zone.addEventListener('drop', function(e) {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      handleFileSelect(input, zone, info);
    }
  });
  
  input.addEventListener('change', function() {
    handleFileSelect(input, zone, info);
  });
}

function handleFileSelect(input, zone, info) {
  const file = input.files[0];
  if (!file) return;
  
  if (file.type !== 'application/pdf') {
    showUploadError(zone, info, 'Please upload a PDF file.');
    input.value = '';
    return;
  }
  
  if (file.size > 10 * 1024 * 1024) {
    showUploadError(zone, info, 'File is too large. Maximum size is 10 MB.');
    input.value = '';
    return;
  }
  
  zone.classList.add('has-file');
  info.innerHTML = '<div class="upload-file-info">' +
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' +
    '<div><strong>' + escapeHtml(file.name) + '</strong><br>' +
    '<span style="font-size:0.8125rem;color:var(--text-secondary)">' + formatFileSize(file.size) + '</span></div></div>';
}

function showUploadError(zone, info, message) {
  zone.classList.remove('has-file');
  info.innerHTML = '<div class="alert alert-error" style="margin:8px 0 0">' +
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>' +
    escapeHtml(message) + '</div>';
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ============ LOADING STATES ============
function showLoading(stages) {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  overlay.classList.add('active');
  
  if (stages && stages.length) {
    const stageEl = overlay.querySelector('.loading-stage');
    let idx = 0;
    stageEl.textContent = stages[0];
    
    const interval = setInterval(function() {
      idx++;
      if (idx < stages.length) {
        stageEl.textContent = stages[idx];
      } else {
        clearInterval(interval);
      }
    }, 1500);
  }
}

function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.remove('active');
}

// ============ SCORE RING ANIMATION ============
function animateScoreRing(elementId, score, maxScore) {
  maxScore = maxScore || 100;
  const el = document.getElementById(elementId);
  if (!el) return;
  
  const circle = el.querySelector('.score-ring-fg');
  const valueEl = el.querySelector('.score-ring-value');
  if (!circle || !valueEl) return;
  
  const radius = circle.getAttribute('r');
  const circumference = 2 * Math.PI * radius;
  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference;
  
  // Animate
  let current = 0;
  const duration = 1200;
  const start = performance.now();
  
  function animate(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    current = eased * score;
    
    const offset = circumference - (current / maxScore) * circumference;
    circle.style.strokeDashoffset = offset;
    valueEl.textContent = Math.round(current);
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }
  
  requestAnimationFrame(animate);
}

// ============ WHAT-IF SIMULATOR ============
function initWhatIf(analysisId) {
  const checkboxes = document.querySelectorAll('.whatif-skill input[type="checkbox"]');
  const scoreDisplay = document.getElementById('whatif-new-score');
  const chartDiv = document.getElementById('whatif-chart');
  
  let debounceTimer;
  
  checkboxes.forEach(function(cb) {
    cb.addEventListener('change', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function() { computeWhatIf(analysisId); }, 300);
    });
  });
}

function computeWhatIf(analysisId) {
  const checked = [];
  document.querySelectorAll('.whatif-skill input[type="checkbox"]:checked').forEach(function(cb) {
    checked.push(cb.value);
  });
  
  fetch('/api/whatif', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysisId, learn_skills: checked })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.error) return;
    
    const scoreEl = document.getElementById('whatif-new-score');
    if (scoreEl) scoreEl.textContent = Math.round(data.new_score);
    
    const gradeEl = document.getElementById('whatif-new-grade');
    if (gradeEl) gradeEl.textContent = data.new_grade;
    
    // Update before/after chart
    if (typeof Plotly !== 'undefined' && document.getElementById('whatif-chart')) {
      var colors = getPlotlyColors();
      Plotly.react('whatif-chart', [{
        x: ['Current', 'Projected'],
        y: [data.current_score, data.new_score],
        type: 'bar',
        marker: { color: [colors.textSecondary, colors.accent] },
        text: [Math.round(data.current_score) + '%', Math.round(data.new_score) + '%'],
        textposition: 'outside'
      }], getPlotlyLayout('Score comparison'), { responsive: true, displayModeBar: false });
    }
    
    // Show best next skill
    const bestEl = document.getElementById('whatif-best-next');
    if (bestEl && data.best_next_skill) {
      bestEl.innerHTML = '<strong>Best next skill to learn:</strong> ' + escapeHtml(data.best_next_skill.name) +
        ' <span class="chip chip-matched">+' + data.best_next_skill.gain.toFixed(1) + ' points</span>';
    }
  })
  .catch(function(err) { console.error('What-if error:', err); });
}

// ============ PLOTLY HELPERS ============
function getPlotlyColors() {
  var style = getComputedStyle(document.documentElement);
  return {
    bg: style.getPropertyValue('--bg-card').trim(),
    text: style.getPropertyValue('--text-primary').trim(),
    textSecondary: style.getPropertyValue('--text-secondary').trim(),
    accent: style.getPropertyValue('--accent').trim(),
    border: style.getPropertyValue('--border').trim(),
    matched: style.getPropertyValue('--matched').trim(),
    partial: style.getPropertyValue('--partial').trim(),
    missing: style.getPropertyValue('--missing').trim(),
    bgPrimary: style.getPropertyValue('--bg-primary').trim(),
  };
}

function getPlotlyLayout(title) {
  var c = getPlotlyColors();
  return {
    title: { text: title, font: { family: 'Inter, sans-serif', size: 14, color: c.text } },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, sans-serif', color: c.textSecondary, size: 12 },
    margin: { l: 50, r: 20, t: 40, b: 40 },
    xaxis: { gridcolor: c.border, linecolor: c.border, zerolinecolor: c.border },
    yaxis: { gridcolor: c.border, linecolor: c.border, zerolinecolor: c.border },
  };
}

// ============ CHAT ASSISTANT ============
function initChat(analysisId) {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const messages = document.getElementById('chat-messages');
  
  function sendMessage(text) {
    if (!text.trim()) return;
    
    // Add user message
    appendMessage(text, 'user');
    input.value = '';
    
    // Fetch response
    fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId, question: text })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      appendMessage(data.answer || 'Sorry, I could not understand that question.', 'bot');
    })
    .catch(function() {
      appendMessage('Something went wrong. Please try again.', 'bot');
    });
  }
  
  function appendMessage(text, role) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + role;
    div.innerHTML = '<div class="chat-bubble">' + escapeHtml(text) + '</div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }
  
  if (sendBtn) {
    sendBtn.addEventListener('click', function() { sendMessage(input.value); });
  }
  if (input) {
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input.value);
      }
    });
  }
  
  // Suggested questions
  document.querySelectorAll('.suggested-q').forEach(function(btn) {
    btn.addEventListener('click', function() {
      sendMessage(this.textContent);
    });
  });
}

// ============ CONFIRM DELETE ============
function confirmDelete(message, formId) {
  if (confirm(message || 'Are you sure? This cannot be undone.')) {
    document.getElementById(formId).submit();
  }
}

// ============ UTILITY ============
function escapeHtml(text) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// CSRF token helper
function getCsrfToken() {
  var el = document.querySelector('input[name="csrf_token"]');
  return el ? el.value : '';
}
