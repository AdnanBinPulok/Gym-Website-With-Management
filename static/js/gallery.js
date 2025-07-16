document.addEventListener('DOMContentLoaded', function() {
    const galleryContainer = document.querySelector('.gallery-swiper');
    
    if (!galleryContainer) return;
    
    // Initialize Swiper
    const gallerySwiper = new Swiper('.gallery-swiper', {
        // Responsive breakpoints
        slidesPerView: 1,
        spaceBetween: 16,
        loop: true,
        autoplay: {
            delay: 5000,
            disableOnInteraction: false,
        },
        speed: 500,
        effect: 'slide',
        
        // Responsive breakpoints
        breakpoints: {
            640: {
                slidesPerView: 1,
                spaceBetween: 16,
            },
            768: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1024: {
                slidesPerView: 3,
                spaceBetween: 24,
            },
        },
        
        // Navigation arrows - using custom buttons
        navigation: {
            nextEl: '.gallery-next-btn',
            prevEl: '.gallery-prev-btn',
        },
        
        // Pagination
        pagination: {
            el: '.gallery-pagination',
            clickable: true,
            dynamicBullets: true,
            dynamicMainBullets: 3,
        },
        
        // Keyboard control
        keyboard: {
            enabled: true,
        },
        
        // Touch events
        touchRatio: 1,
        touchAngle: 45,
        
        // Events
        on: {
            init: function () {
                updatePaginationStyle();
                updateNavigationButtons();
            },
            slideChange: function () {
                updatePaginationStyle();
            },
            reachBeginning: function() {
                updateNavigationButtons();
            },
            reachEnd: function() {
                updateNavigationButtons();
            },
        },
    });
    
    // Custom pagination styling
    function updatePaginationStyle() {
        const bullets = document.querySelectorAll('.gallery-pagination .swiper-pagination-bullet');
        bullets.forEach((bullet) => {
            if (bullet.classList.contains('swiper-pagination-bullet-active')) {
                bullet.style.backgroundColor = '#ff6b35';
            } else {
                bullet.style.backgroundColor = '#6b7280';
            }
        });
    }
    
    // Update navigation button states
    function updateNavigationButtons() {
        const prevBtn = document.querySelector('.gallery-prev-btn');
        const nextBtn = document.querySelector('.gallery-next-btn');
        
        if (prevBtn && nextBtn) {
            // For loop mode, buttons are always enabled
            prevBtn.style.opacity = '0.75';
            nextBtn.style.opacity = '0.75';
        }
    }
    
    // Pause autoplay on hover
    galleryContainer.addEventListener('mouseenter', function() {
        gallerySwiper.autoplay.stop();
    });
    
    galleryContainer.addEventListener('mouseleave', function() {
        gallerySwiper.autoplay.start();
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        gallerySwiper.update();
    });
    
    // Add hover effects to navigation buttons
    const navButtons = document.querySelectorAll('.gallery-prev-btn, .gallery-next-btn');
    navButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.opacity = '1';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.opacity = '0.75';
        });
    });
});
