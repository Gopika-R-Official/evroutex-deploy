console.log('✅ EV ROUTEX - Google Maps FIXED!');
window.navigateFullRoute = function(orders) {
    console.log('🚀 Orders:', orders);
    if (!orders || orders.length === 0) {
        alert('No orders found!');
        return;
    }
    const waypoints = orders.map(o => ${o.latitude},).join('|');
    const url = https://www.google.com/maps/dir/?api=1&waypoints=&travelmode=driving;
    console.log('📱 Opening Maps:', url);
    window.open(url, '_blank');
};
console.log('✅ Maps function ready!');
