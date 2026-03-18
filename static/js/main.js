// ============================================
// RESIDENCIAL PARK CLUB - Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
    initMobileMenu();
    initHeroSlideshow();
    initFuturoCarousel();
    initScrollAnimations();
    initAutoAlertDismiss();
    initLightbox();
});

// Navbar scroll effect
function initNavbar() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;

    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });
}

// Mobile menu toggle
function initMobileMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
        menu.classList.toggle('open');
        toggle.classList.toggle('active');
    });

    menu.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            menu.classList.remove('open');
            toggle.classList.remove('active');
        });
    });
}

// ============ HERO SLIDESHOW LENTO ============
// Transição suave a cada 6 segundos com fade de 2s
function initHeroSlideshow() {
    const slideshow = document.getElementById('heroSlideshow');
    const indicators = document.getElementById('heroIndicators');
    if (!slideshow) return;

    const slides = slideshow.querySelectorAll('.hero-slide');
    const dots = indicators ? indicators.querySelectorAll('.hero-indicator') : [];
    if (slides.length <= 1) return;

    let currentIndex = 0;
    let interval = null;

    function goToSlide(index) {
        // Remover active do slide atual
        slides[currentIndex].classList.remove('active');
        if (dots[currentIndex]) dots[currentIndex].classList.remove('active');

        // Ativar novo slide
        currentIndex = index;
        slides[currentIndex].classList.add('active');
        if (dots[currentIndex]) dots[currentIndex].classList.add('active');
    }

    function nextSlide() {
        const next = (currentIndex + 1) % slides.length;
        goToSlide(next);
    }

    // Iniciar intervalo - 6 segundos por foto (lento e elegante)
    function startInterval() {
        interval = setInterval(nextSlide, 6000);
    }

    function resetInterval() {
        clearInterval(interval);
        startInterval();
    }

    // Click nos indicadores
    dots.forEach((dot, i) => {
        dot.addEventListener('click', () => {
            if (i === currentIndex) return;
            goToSlide(i);
            resetInterval();
        });
    });

    // Pausar no hover
    slideshow.closest('.hero').addEventListener('mouseenter', () => {
        clearInterval(interval);
    });

    slideshow.closest('.hero').addEventListener('mouseleave', () => {
        startInterval();
    });

    startInterval();
}

// ============ CARROSSEL PROJETOS FUTUROS ============
function initFuturoCarousel() {
    const carousel = document.getElementById('futuroCarousel');
    if (!carousel) return;

    const track = document.getElementById('futuroTrack');
    const prevBtn = document.getElementById('futuroPrev');
    const nextBtn = document.getElementById('futuroNext');
    const slides = track.querySelectorAll('.futuro-slide');

    if (slides.length === 0) return;

    let position = 0;

    function getSlideWidth() {
        return slides[0].offsetWidth + 20; // width + gap
    }

    function getVisibleCount() {
        const w = carousel.offsetWidth;
        if (w < 768) return 1;
        if (w < 1024) return 2;
        return 3;
    }

    function getMaxPosition() {
        return Math.max(0, slides.length - getVisibleCount());
    }

    function updateTrack() {
        const offset = position * getSlideWidth();
        track.style.transform = `translateX(-${offset}px)`;
    }

    function updateButtons() {
        if (prevBtn) prevBtn.style.opacity = position === 0 ? '0.3' : '1';
        if (nextBtn) nextBtn.style.opacity = position >= getMaxPosition() ? '0.3' : '1';
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (position > 0) {
                position--;
                updateTrack();
                updateButtons();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (position < getMaxPosition()) {
                position++;
                updateTrack();
                updateButtons();
            }
        });
    }

    // Touch/swipe support
    let touchStartX = 0;
    let touchEndX = 0;

    track.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    track.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        const diff = touchStartX - touchEndX;

        if (Math.abs(diff) > 50) {
            if (diff > 0 && position < getMaxPosition()) {
                position++;
            } else if (diff < 0 && position > 0) {
                position--;
            }
            updateTrack();
            updateButtons();
        }
    }, { passive: true });

    // Recalcular no resize
    window.addEventListener('resize', () => {
        if (position > getMaxPosition()) {
            position = getMaxPosition();
        }
        updateTrack();
        updateButtons();
    });

    updateButtons();
}

// Scroll reveal animations
function initScrollAnimations() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    if (!elements.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    elements.forEach(el => observer.observe(el));
}

// Auto-dismiss message modal after 4 seconds
function initAutoAlertDismiss() {
    const modal = document.getElementById('msgModal');
    if (!modal) return;
    setTimeout(() => {
        modal.style.opacity = '0';
        modal.style.transition = 'opacity .4s ease';
        setTimeout(() => modal.remove(), 400);
    }, 4000);
}

// Lightbox for gallery
function initLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    const lightboxContent = lightbox.querySelector('.lightbox-content');
    const closeBtn = lightbox.querySelector('.lightbox-close');

    document.querySelectorAll('[data-lightbox]').forEach(item => {
        item.addEventListener('click', () => {
            const src = item.dataset.lightbox;
            const type = item.dataset.type || 'image';

            lightboxContent.innerHTML = '';

            if (type === 'video') {
                const video = document.createElement('video');
                video.src = src;
                video.controls = true;
                video.autoplay = true;
                lightboxContent.appendChild(video);
            } else {
                const img = document.createElement('img');
                img.src = src;
                img.alt = 'Residencial Park Club';
                lightboxContent.appendChild(img);
            }

            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', closeLightbox);
    }

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) closeLightbox();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
    });

    function closeLightbox() {
        lightbox.classList.remove('active');
        document.body.style.overflow = '';
        const video = lightboxContent.querySelector('video');
        if (video) video.pause();
    }
}

// ============ VER MAIS FOTOS ============
function mostrarMaisFotos() {
    const hidden = document.querySelectorAll('.gallery-hidden');
    const btn = document.getElementById('btnVerMais');
    let shown = 0;

    hidden.forEach(item => {
        if (shown < 12) {
            item.classList.remove('gallery-hidden');
            item.style.animation = 'fadeInUp .5s ease both';
            item.style.animationDelay = (shown * 0.05) + 's';
            shown++;
        }
    });

    // Recriar ícones lucide para os novos itens
    lucide.createIcons();

    // Reinicializar lightbox para os novos itens
    initLightbox();

    // Atualizar contador ou esconder botão
    const remaining = document.querySelectorAll('.gallery-hidden').length;
    if (remaining === 0) {
        btn.style.display = 'none';
    } else {
        document.getElementById('contadorRestante').textContent = '(+' + remaining + ')';
    }
}

// ============ MODAL DE AVISOS ============
document.querySelectorAll('.hero-aviso-card-item').forEach(card => {
    card.addEventListener('click', () => {
        const modal = document.getElementById('avisoModal');
        if (!modal) return;
        document.getElementById('avisoModalTitulo').textContent = card.dataset.avisoTitulo;
        document.getElementById('avisoModalConteudo').textContent = card.dataset.avisoConteudo;
        document.getElementById('avisoModalMeta').textContent = card.dataset.avisoAutor + ' · ' + card.dataset.avisoData;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    });
});

// Fechar modal ao clicar fora
document.getElementById('avisoModal')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// CPF mask
document.querySelectorAll('input[name="cpf"]').forEach(input => {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '');
        if (v.length > 11) v = v.slice(0, 11);
        v = v.replace(/(\d{3})(\d)/, '$1.$2');
        v = v.replace(/(\d{3})(\d)/, '$1.$2');
        v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        e.target.value = v;
    });
});

// Phone mask
document.querySelectorAll('input[name="telefone"], input[name="contato_telefone"]').forEach(input => {
    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/\D/g, '');
        if (v.length > 11) v = v.slice(0, 11);
        if (v.length > 6) {
            v = v.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
        } else if (v.length > 2) {
            v = v.replace(/(\d{2})(\d{0,5})/, '($1) $2');
        }
        e.target.value = v;
    });
});

// Máscara de valor monetário (R$ 1.234,56)
document.querySelectorAll('input[name="valor"], input[type="number"][name="valor"]').forEach(input => {
    // Trocar type para text para permitir formatação
    input.type = 'text';
    input.inputMode = 'numeric';
    input.placeholder = 'R$ 0,00';

    // Formatar valor existente ao carregar
    if (input.value && !isNaN(parseFloat(input.value))) {
        input.value = formatarMoeda(parseFloat(input.value) * 100);
    }

    input.addEventListener('input', (e) => {
        let digits = e.target.value.replace(/\D/g, '');
        if (digits === '') { e.target.value = ''; return; }
        e.target.value = formatarMoeda(parseInt(digits));
    });

    // Ao enviar o form, converter de volta para número
    input.closest('form')?.addEventListener('submit', () => {
        let digits = input.value.replace(/\D/g, '');
        input.value = digits ? (parseInt(digits) / 100).toFixed(2) : '0';
    });
});

function formatarMoeda(centavos) {
    let v = (centavos / 100).toFixed(2);
    let parts = v.split('.');
    let inteiro = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return 'R$ ' + inteiro + ',' + parts[1];
}

// Máscara de área (m²) - aceita decimal com vírgula
document.querySelectorAll('input[name="area"]').forEach(input => {
    input.type = 'text';
    input.inputMode = 'decimal';
    input.placeholder = 'Ex: 43,73';

    if (input.value && !isNaN(parseFloat(input.value))) {
        input.value = parseFloat(input.value).toFixed(2).replace('.', ',');
    }

    input.addEventListener('input', (e) => {
        let v = e.target.value.replace(/[^\d,]/g, '');
        // Só permite uma vírgula
        let parts = v.split(',');
        if (parts.length > 2) v = parts[0] + ',' + parts.slice(1).join('');
        // Máximo 2 decimais
        if (parts[1] && parts[1].length > 2) v = parts[0] + ',' + parts[1].slice(0, 2);
        e.target.value = v;
    });

    input.closest('form')?.addEventListener('submit', () => {
        input.value = input.value.replace(',', '.') || '0';
    });
});
