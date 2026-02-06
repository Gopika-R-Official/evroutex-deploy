// Smooth scrolling and animations
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Loading animation
window.addEventListener('load', function() {
    document.body.classList.add('loaded');
});

// Form validation
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let valid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.style.borderColor = '#ef4444';
                valid = false;
            } else {
                field.style.borderColor = '#10b981';
            }
        });
        
        if (!valid) {
            e.preventDefault();
            alert('Please fill all required fields');
        }
    });
});
// EV ROUTEX - Main JavaScript (Empty but prevents 404)
console.log('EV ROUTEX loaded successfully!');
window.EVROUTEX = true;
// EV ROUTEX - Main JavaScript (Fixes 404)
console.log('✅ EV ROUTEX main.js LOADED!');
window.EVROUTEX = true;

// Auto-fix Google Maps navigation
window.navigateFullRoute = function(route) {
    console.log('Navigating route:', route);
    if (route && route.length > 0) {
        try {
            const waypoints = route.map(stop => `${stop.lat},${stop.lng}`).join('|');
            const url = `https://www.google.com/maps/dir/?api=1&waypoints=${waypoints}&travelmode=driving`;
            window.open(url, '_blank');
            console.log('✅ Maps opened:', url);
        } catch(e) {
            console.error('Maps error:', e);
            alert('Please use individual navigation buttons');
        }
    }
};
