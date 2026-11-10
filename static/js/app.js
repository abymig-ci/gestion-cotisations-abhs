document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    
    // 1. Ouvrir/Fermer avec le bouton hamburger
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function(e) {
            e.stopPropagation(); // Empêche la propagation
            sidebar.classList.toggle('show');
        });
    }

    // 2. Fermer le menu si on clique en dehors (méthode robuste sur tout le document)
    document.addEventListener('click', function(event) {
        if (sidebar && sidebar.classList.contains('show')) {
            // Si le clic n'est ni dans la sidebar, ni sur le bouton toggle
            if (!sidebar.contains(event.target) && (!toggleBtn || !toggleBtn.contains(event.target))) {
                sidebar.classList.remove('show');
            }
        }
    });
    
    // 3. Fermer le menu si on clique sur un lien du menu (navigation)
    if (sidebar) {
        const sidebarLinks = sidebar.querySelectorAll('a');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (sidebar.classList.contains('show')) {
                    sidebar.classList.remove('show');
                }
            });
        });
    }

    // 4. Auto-hide des alertes après 4 secondes
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert-custom');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 4000);
});