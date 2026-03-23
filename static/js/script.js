document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        const currentTheme = localStorage.getItem('theme') || 'light-mode';
        document.body.className = currentTheme;
        updateThemeIcon(currentTheme);

        themeBtn.addEventListener('click', () => {
            if (document.body.classList.contains('light-mode')) {
                document.body.className = 'dark-mode';
                localStorage.setItem('theme', 'dark-mode');
                updateThemeIcon('dark-mode');
            } else {
                document.body.className = 'light-mode';
                localStorage.setItem('theme', 'light-mode');
                updateThemeIcon('light-mode');
            }
        });
    }

    function updateThemeIcon(theme) {
        if(!themeBtn) return;
        const icon = themeBtn.querySelector('i');
        if (theme === 'dark-mode') {
            icon.className = 'fa-solid fa-sun';
        } else {
            icon.className = 'fa-solid fa-moon';
        }
    }

    // Password Toggle
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (input.type === 'password') {
                input.type = 'text';
                this.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                this.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });

    // Close Flash Messages
    const closeBtns = document.querySelectorAll('.close-alert');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.style.opacity = '0';
            setTimeout(() => this.parentElement.remove(), 300);
        });
    });

    setTimeout(() => {
        const alerts = document.querySelectorAll('.flash-alert');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);
});
