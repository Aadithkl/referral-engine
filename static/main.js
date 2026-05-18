// ================================================================
// REFERRAL ENGINE — main.js
// Lenis + GSAP + Chart.js + Custom Cursor + Interactions
// ================================================================

// --- LENIS SMOOTH SCROLL ---------------------------------------
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  smoothWheel: true,
});

function raf(time) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}
requestAnimationFrame(raf);

// --- GSAP + SCROLLTRIGGER --------------------------------------
gsap.registerPlugin(ScrollTrigger);

lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => { lenis.raf(time * 1000); });
gsap.ticker.lagSmoothing(0);

// --- NAV -------------------------------------------------------
window.addEventListener('scroll', () => {
  document.getElementById('nav').classList.toggle('visible', window.scrollY > 80);
});

// --- CURSOR V ARROW ---------------------------------------------
const heroVideo = document.getElementById('hero-video');
const cursorArrow = document.getElementById('cursor-arrow');
let arrowVisible = false;

if (cursorArrow && heroVideo) {
  heroVideo.addEventListener('timeupdate', () => {
    if (!arrowVisible && heroVideo.currentTime >= heroVideo.duration - 1.5) {
      arrowVisible = true;
      cursorArrow.classList.add('visible');
    }
  });
  heroVideo.addEventListener('ended', () => {
    if (!arrowVisible) { arrowVisible = true; cursorArrow.classList.add('visible'); }
  });
  setTimeout(() => {
    if (!arrowVisible) { arrowVisible = true; cursorArrow.classList.add('visible'); }
  }, 3000);

  cursorArrow.addEventListener('click', () => {
    const pain1 = document.getElementById('pain1');
    if (pain1) lenis.scrollTo(pain1);
  });
}

// Update cursor arrow position in cursor lerp loop
// It tracks ~40px below the cursor

// --- CUSTOM CURSOR ---------------------------------------------
let mx = 0, my = 0, rx = 0, ry = 0;
const dot = document.getElementById('cursor-dot');
const ring = document.getElementById('cursor-ring');

if (dot && ring) {
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    dot.style.left = mx + 'px';
    dot.style.top = my + 'px';
  });

  (function lerpCursor() {
    rx += (mx - rx) * 0.12;
    ry += (my - ry) * 0.12;
    ring.style.left = rx + 'px';
    ring.style.top = ry + 'px';
    if (cursorArrow) {
      cursorArrow.style.left = mx + 'px';
      cursorArrow.style.top = (my + 36) + 'px';
    }
    requestAnimationFrame(lerpCursor);
  })();

  const hoverTargets = 'a, button, .btn-primary, .btn-ghost, input, .arch-card, .pipe-step, .video-frame';
  document.querySelectorAll(hoverTargets).forEach(el => {
    el.addEventListener('mouseenter', () => {
      ring.style.width = '48px';
      ring.style.height = '48px';
      ring.style.borderColor = 'rgba(239,159,39,0.8)';
      dot.style.width = '3px';
      dot.style.height = '3px';
    });
    el.addEventListener('mouseleave', () => {
      ring.style.width = '28px';
      ring.style.height = '28px';
      ring.style.borderColor = 'rgba(239,159,39,0.5)';
      dot.style.width = '5px';
      dot.style.height = '5px';
    });
  });
}

// --- MAGNETIC BUTTONS ------------------------------------------
document.querySelectorAll('.magnetic').forEach(btn => {
  btn.addEventListener('mousemove', e => {
    const r = btn.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const dx = (e.clientX - cx) * 0.25;
    const dy = (e.clientY - cy) * 0.25;
    btn.style.transform = `translate(${dx}px, ${dy}px)`;
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.transform = 'translate(0,0)';
    btn.style.transition = 'transform 0.5s cubic-bezier(0.23,1,0.32,1)';
  });
  btn.addEventListener('mouseenter', () => {
    btn.style.transition = 'transform 0.1s ease';
  });
});

// --- SPLIT HEADLINES (dynamic word wrapping) -------------------
function splitHeadlines() {
  document.querySelectorAll('.split-headline').forEach(el => {
    if (el.dataset.split) return;
    el.dataset.split = 'true';
    const text = el.textContent.trim();
    const words = text.split(/\s+/);
    el.innerHTML = '';
    words.forEach(word => {
      const wordSpan = document.createElement('span');
      wordSpan.className = 'word';
      const inner = document.createElement('span');
      inner.className = 'word-inner';
      inner.textContent = word;
      wordSpan.appendChild(inner);
      el.appendChild(wordSpan);
      // re-add space between words
      el.appendChild(document.createTextNode(' '));
    });
  });
}
splitHeadlines();

// --- HEADLINE ANIMATIONS ---------------------------------------
function animateHeadline(el, opts = {}) {
  const words = el.querySelectorAll('.word-inner');
  if (!words.length) return;
  const config = Object.assign({
    y: '110%', opacity: 0, yTo: '0%', opacityTo: 1,
    duration: 0.75, stagger: 0.06, ease: 'power3.out',
    scrollTrigger: null
  }, opts);
  const anim = { y: config.yTo, opacity: config.opacityTo, duration: config.duration, ease: config.ease, stagger: config.stagger };
  if (config.scrollTrigger) anim.scrollTrigger = config.scrollTrigger;
  gsap.fromTo(words, { y: config.y, opacity: config.opacity }, anim);
}

// Hero headline — no scroll trigger, delayed start
function animateHero() {
  const heroHeadline = document.querySelector('.hero-headline');
  if (!heroHeadline) return;
  const words = heroHeadline.querySelectorAll('.word-inner');
  if (!words.length) return;
  gsap.fromTo(words,
    { y: '110%', opacity: 0 },
    { y: '0%', opacity: 1, duration: 0.75, ease: 'power3.out', stagger: 0.06, delay: 0.3 }
  );
  // Hero sub and CTA
  gsap.fromTo('.hero-sub', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, delay: 0.9 });
  gsap.fromTo('.hero .btn-primary', { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, delay: 1.1 });
  gsap.fromTo('.eyebrow-pill', { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, delay: 0.5 });
}

// Section 2 — Pain 1
function animatePain1() {
  const headline = document.querySelector('#pain1 .split-headline');
  if (headline) {
    animateHeadline(headline, {
      scrollTrigger: { trigger: '#pain1', start: 'top 80%' }
    });
  }
  gsap.fromTo('#pain1 .pain-video-wrap', { opacity: 0, x: -40 }, {
    opacity: 1, x: 0, duration: 0.7, ease: 'power2.out',
    scrollTrigger: { trigger: '#pain1', start: 'top 75%' }
  });
  gsap.fromTo('#pain1 .pain-text > *:not(h2)', { opacity: 0, x: 60 }, {
    opacity: 1, x: 0, duration: 0.6, stagger: 0.1, ease: 'power2.out',
    scrollTrigger: { trigger: '#pain1', start: 'top 75%' }
  });
}

// Section 3 — Pain 2
function animatePain2() {
  const headline = document.querySelector('#pain2 .split-headline');
  if (headline) {
    animateHeadline(headline, {
      scrollTrigger: { trigger: '#pain2', start: 'top 80%' }
    });
  }
  gsap.fromTo('#pain2 .pain-video-wrap', { opacity: 0, x: 40 }, {
    opacity: 1, x: 0, duration: 0.7, ease: 'power2.out',
    scrollTrigger: { trigger: '#pain2', start: 'top 75%' }
  });
  gsap.fromTo('#pain2 .pain-text > *:not(h2)', { opacity: 0, x: -60 }, {
    opacity: 1, x: 0, duration: 0.6, stagger: 0.1, ease: 'power2.out',
    scrollTrigger: { trigger: '#pain2', start: 'top 75%' }
  });
}

// Section 4 — The Curve
function animateCurve() {
  const headline = document.querySelector('#curve .split-headline');
  if (headline) {
    animateHeadline(headline, {
      scrollTrigger: { trigger: '#curve', start: 'top 80%' }
    });
  }
  gsap.fromTo('#curve .curve-text > *', { opacity: 0, y: 40 }, {
    opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out',
    scrollTrigger: { trigger: '#curve', start: 'top 75%' }
  });
  gsap.fromTo('#curve .curve-video-top', { opacity: 0, y: 30 }, {
    opacity: 1, y: 0, duration: 0.6, ease: 'power2.out',
    scrollTrigger: { trigger: '#curve', start: 'top 80%' }
  });
}

// --- SUNRISE CANVAS: Pixel breakdown + day/night transition -----
const sunriseCanvas = document.getElementById('sunrise-canvas');
let sunriseCtx = null;
let sunriseActive = false;

if (sunriseCanvas) {
  sunriseCtx = sunriseCanvas.getContext('2d');
  sunriseCanvas.width = window.innerWidth;
  sunriseCanvas.height = window.innerHeight;

  class Pixel {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.vx = (Math.random() - 0.5) * 2;
      this.vy = (Math.random() - 0.5) * 2 - 1;
      this.life = 1;
      this.decay = Math.random() * 0.01 + 0.005;
      this.size = Math.random() * 2 + 1;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      this.life -= this.decay;
    }
    draw() {
      sunriseCtx.fillStyle = `rgba(255, 80, 40, ${this.life * 0.4})`;
      sunriseCtx.fillRect(this.x, this.y, this.size, this.size);
    }
  }

  let pixels = [];
  let scrollProgress = 0;
  const mechanicsSection = document.querySelector('[data-section="mechanics"]');

  function getTriggerZone() {
    if (!mechanicsSection) return { start: 0, end: 1 };
    const curveSection = document.getElementById('curve');
    const triggerStart = curveSection
      ? curveSection.offsetTop + curveSection.offsetHeight * 0.4
      : mechanicsSection.offsetTop - window.innerHeight * 1.2;
    const triggerEnd = mechanicsSection.offsetTop + window.innerHeight * 1.2;
    return { start: triggerStart, end: triggerEnd };
  }

  function animateSunrise() {
    if (!sunriseCtx) return;
    const { start, end } = getTriggerZone();
    const viewportBottom = window.scrollY + window.innerHeight;
    scrollProgress = Math.max(0, Math.min(1, (viewportBottom - start) / (end - start)));

    if (scrollProgress > 0 && !sunriseActive) {
      sunriseActive = true;
      sunriseCanvas.classList.add('active');
    }

    // Background: night (#0a0a2e) → morning (#faf9f6)
    const r = Math.round(10 + (250 - 10) * scrollProgress);
    const g = Math.round(10 + (249 - 10) * scrollProgress);
    const b = Math.round(46 + (246 - 46) * scrollProgress);
    sunriseCtx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    sunriseCtx.fillRect(0, 0, sunriseCanvas.width, sunriseCanvas.height);

    // Sun: rises from bottom-right
    const sunX = sunriseCanvas.width * 0.75;
    const sunStartY = sunriseCanvas.height;
    const sunEndY = sunriseCanvas.height * 0.15;
    const sunY = sunStartY + (sunEndY - sunStartY) * scrollProgress;
    const sunRadius = 80 + scrollProgress * 40;

    // Glow behind sun
    const sunGlow = sunriseCtx.createRadialGradient(sunX, sunY, 0, sunX, sunY, sunRadius * 1.5);
    sunGlow.addColorStop(0, `rgba(255, 200, 80, ${0.3 * scrollProgress})`);
    sunGlow.addColorStop(1, 'rgba(255, 100, 40, 0)');
    sunriseCtx.fillStyle = sunGlow;
    sunriseCtx.fillRect(0, 0, sunriseCanvas.width, sunriseCanvas.height);

    // Sun itself
    sunriseCtx.fillStyle = `rgb(255, ${150 + scrollProgress * 80}, ${40 + scrollProgress * 60})`;
    sunriseCtx.beginPath();
    sunriseCtx.arc(sunX, sunY, sunRadius, 0, Math.PI * 2);
    sunriseCtx.fill();

    // Pixel rain
    if (scrollProgress < 0.9) {
      for (let i = 0; i < 3; i++) {
        const px = Math.random() * sunriseCanvas.width;
        const py = Math.random() * sunriseCanvas.height * (1 - scrollProgress);
        pixels.push(new Pixel(px, py));
      }
    }
    pixels = pixels.filter(p => p.life > 0);
    pixels.forEach(p => { p.update(); p.draw(); });

    requestAnimationFrame(animateSunrise);
  }
  animateSunrise();

  window.addEventListener('resize', () => {
    sunriseCanvas.width = window.innerWidth;
    sunriseCanvas.height = window.innerHeight;
  });
}

// --- MECHANICS SECTION ANIMATIONS -------------------------------
function animateMechanics() {
  const headline = document.querySelector('#mechanics .split-headline');
  if (headline) {
    animateHeadline(headline, {
      scrollTrigger: { trigger: '#mechanics', start: 'top 85%' }
    });
  }
  gsap.fromTo('.wf-step', { opacity: 0, y: 30 }, {
    opacity: 1, y: 0, duration: 0.4, stagger: 0.1, ease: 'power2.out',
    scrollTrigger: { trigger: '.wf-vertical', start: 'top 85%' }
  });
  gsap.fromTo('.wf-agent-block', { opacity: 0, y: 30 }, {
    opacity: 1, y: 0, duration: 0.4, ease: 'power2.out',
    scrollTrigger: { trigger: '.wf-vertical', start: 'top 82%' }
  });
  gsap.fromTo('.wf-arrow-down', { opacity: 0 }, {
    opacity: 1, duration: 0.3, stagger: 0.08,
    scrollTrigger: { trigger: '.wf-vertical', start: 'top 85%' }
  });
  gsap.fromTo('.mech-col', { opacity: 0, y: 40 }, {
    opacity: 1, y: 0, duration: 0.6, stagger: 0.15, ease: 'power2.out',
    scrollTrigger: { trigger: '.mech-cols', start: 'top 80%' }
  });
}

// --- CHART.JS — Reward Curve -----------------------------------
let chartInitialized = false;

function initChart() {
  if (chartInitialized) return;
  chartInitialized = true;

  const ctx = document.getElementById('rewardChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
      datasets: [{
        label: 'credits',
        data: [10, 10, 7, 4, 7, 15, 25, 22, 20, 20],
        borderColor: '#EF9F27',
        backgroundColor: 'rgba(239,159,39,0.08)',
        borderWidth: 1.5,
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 3,
        pointHoverBackgroundColor: '#EF9F27',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 2000, easing: 'easeOutQuart' },
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0d0d1a',
          borderColor: 'rgba(239,159,39,0.3)',
          borderWidth: 1,
          titleFont: { family: 'DM Mono', size: 12 },
          bodyFont: { family: 'DM Mono', size: 12 },
          titleColor: '#5C5C7A',
          bodyColor: '#EEEEF5',
          padding: 12,
          cornerRadius: 0,
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#5C5C7A', font: { family: 'DM Mono', size: 11 } },
          border: { color: 'rgba(255,255,255,0.07)' }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
          ticks: { color: '#5C5C7A', font: { family: 'DM Mono', size: 11 }, padding: 8, callback: v => v },
          border: { display: false }
        }
      }
    },
    plugins: [{
      id: 'customCanvasBackground',
      beforeDraw: (chart) => {
        const { ctx, chartArea } = chart;
        ctx.save();
        ctx.fillStyle = '#0d0d1a';
        ctx.fillRect(chartArea.left, chartArea.top, chartArea.right - chartArea.left, chartArea.bottom - chartArea.top);
        ctx.restore();
      }
    }]
  });
}

// Init chart when section scrolls into view
ScrollTrigger.create({
  trigger: '#curve .curve-chart-wrap',
  start: 'top 85%',
  onEnter: initChart,
  once: true
});

// --- SPLASH SCREEN — click to enter & unmute --------------------
let audioOn = false;
const soundBtn = document.getElementById('sound-toggle');

function enableAudio() {
  if (audioOn) return;
  audioOn = true;
  document.querySelectorAll('video').forEach(v => {
    v.muted = false;
    v.volume = 0.7;
  });
  if (soundBtn) { soundBtn.textContent = '\u266B ON'; soundBtn.classList.add('on'); }
}

const splash = document.getElementById('splash');
if (splash) {
  const dismissSplash = () => {
    enableAudio();
    const heroVid = document.getElementById('hero-video');
    if (heroVid) heroVid.play().catch(() => {});
    splash.classList.add('exit');
    splash.addEventListener('transitionend', () => splash.remove(), { once: true });
    setTimeout(() => { if (splash.parentNode) splash.remove(); }, 1200);
  };
  splash.addEventListener('click', dismissSplash);
  splash.addEventListener('touchstart', dismissSplash, { passive: true });
  splash.addEventListener('keydown', (e) => { dismissSplash(); });
}

if (soundBtn) {
  soundBtn.textContent = '\u266B OFF';
  soundBtn.classList.remove('on');
  soundBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const videos = document.querySelectorAll('video');
    if (audioOn) {
      audioOn = false;
      videos.forEach(v => { v.muted = true; });
      soundBtn.textContent = '\u266B OFF';
      soundBtn.classList.remove('on');
    } else {
      enableAudio();
    }
  });
}

// --- VIDEO SCROLL PLAY/PAUSE (only one plays at a time) ----------
let currentlyPlayingVideo = null;

function pauseAllVideos() {
  document.querySelectorAll('video').forEach(v => { v.pause(); });
  currentlyPlayingVideo = null;
}

function playVideoExclusively(video) {
  if (currentlyPlayingVideo && currentlyPlayingVideo !== video) {
    currentlyPlayingVideo.pause();
  }
  video.play().catch(() => {});
  currentlyPlayingVideo = video;
}

const videoObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const video = entry.target;
    if (entry.isIntersecting && entry.intersectionRatio >= 0.25) {
      playVideoExclusively(video);
    } else {
      video.pause();
      if (currentlyPlayingVideo === video) currentlyPlayingVideo = null;
    }
  });
}, { threshold: 0.25 });

document.querySelectorAll('video[data-video]').forEach(v => {
  videoObserver.observe(v);
});

const heroVid = document.getElementById('hero-video');
if (heroVid) {
  const heroObs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && entry.intersectionRatio >= 0.25) {
        playVideoExclusively(heroVid);
      } else {
        heroVid.pause();
        if (currentlyPlayingVideo === heroVid) currentlyPlayingVideo = null;
      }
    });
  }, { threshold: 0.25 });
  heroObs.observe(heroVid);
}

// Ensure all videos start muted (autoplay policy)
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('video').forEach(v => {
    v.muted = true;
  });
});

// --- INIT ALL ANIMATIONS ---------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  animateHero();
  animatePain1();
  animatePain2();
  animateCurve();
  animateMechanics();
});

// Refresh ScrollTrigger after everything loads
window.addEventListener('load', () => {
  ScrollTrigger.refresh();
});
