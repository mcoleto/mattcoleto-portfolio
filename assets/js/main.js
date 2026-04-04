/* ============================================================
   DARK SPECTRUM — main.js
   Nav scroll, mobile menu, filter, scroll reveal, parallax
   ============================================================ */

(function () {
  'use strict';

  /* ── Nav: scroll class + hamburger ─────────────────────── */
  const nav       = document.getElementById('main-nav');
  const hamburger = document.getElementById('nav-hamburger');
  const navLinks  = document.getElementById('nav-links');

  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('nav--scrolled', window.scrollY > 40);
    }, { passive: true });
  }

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      const open = hamburger.classList.toggle('is-open');
      navLinks.classList.toggle('is-open', open);
      hamburger.setAttribute('aria-expanded', open);
      document.body.style.overflow = open ? 'hidden' : '';
    });

    // Close on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('is-open');
        navLinks.classList.remove('is-open');
        hamburger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      });
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navLinks.classList.contains('is-open')) {
        hamburger.classList.remove('is-open');
        navLinks.classList.remove('is-open');
        hamburger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });
  }

  /* ── Scroll reveal ──────────────────────────────────────── */
  const revealEls = document.querySelectorAll('.reveal');

  if (revealEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealEls.forEach(el => observer.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add('is-visible'));
  }

  /* ── Event filter ───────────────────────────────────────── */
  const filterBtns  = document.querySelectorAll('.filter-btn');
  const eventCards  = document.querySelectorAll('.event-card[data-category]');

  if (filterBtns.length && eventCards.length) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const filter = btn.dataset.filter;

        eventCards.forEach(card => {
          const show = filter === 'all' || card.dataset.category === filter;
          card.style.opacity    = '0';
          card.style.transform  = 'scale(0.96)';

          setTimeout(() => {
            card.style.display = show ? '' : 'none';
            if (show) {
              requestAnimationFrame(() => {
                card.style.opacity   = '1';
                card.style.transform = 'scale(1)';
              });
            }
          }, 150);
        });
      });
    });
  }

  /* ── Hero subtle parallax on scroll ────────────────────── */
  const heroBg = document.querySelector('.hero__bg');
  if (heroBg) {
    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      if (scrollY < window.innerHeight) {
        heroBg.style.transform = `translateY(${scrollY * 0.25}px)`;
      }
    }, { passive: true });
  }

  /* ── Animated counter for stats ─────────────────────────── */
  function animateCounter(el, target, suffix, duration) {
    const start     = performance.now();
    const numTarget = parseFloat(target);
    const isDecimal = target.includes('.');

    function update(time) {
      const elapsed  = time - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease     = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const value    = numTarget * ease;
      const display  = isDecimal ? value.toFixed(1) : Math.round(value).toLocaleString();

      el.textContent = display + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  const statNumbers = document.querySelectorAll('.stat-item__number[data-target]');
  if (statNumbers.length && 'IntersectionObserver' in window) {
    const statsObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el     = entry.target;
          const target = el.dataset.target;
          const suffix = el.dataset.suffix || '';
          animateCounter(el, target, suffix, 1800);
          statsObserver.unobserve(el);
        }
      });
    }, { threshold: 0.5 });

    statNumbers.forEach(el => statsObserver.observe(el));
  }

  /* ── Contact form: Formspree async submit ───────────────── */
  const form = document.getElementById('contact-form');
  if (form) {
    const successMsg = document.getElementById('form-success');
    const errorMsg   = document.getElementById('form-error');
    const submitBtn  = form.querySelector('.form-submit');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      submitBtn.textContent = 'Sending…';
      submitBtn.disabled    = true;

      try {
        const res = await fetch(form.action, {
          method:  'POST',
          body:    new FormData(form),
          headers: { 'Accept': 'application/json' },
        });

        if (res.ok) {
          form.reset();
          if (successMsg) { successMsg.style.display = 'block'; }
          submitBtn.textContent = 'Message Sent ✓';
        } else {
          throw new Error('Server error');
        }
      } catch {
        if (errorMsg) { errorMsg.style.display = 'block'; }
        submitBtn.textContent = 'Send Message';
        submitBtn.disabled    = false;
      }
    });
  }

})();
