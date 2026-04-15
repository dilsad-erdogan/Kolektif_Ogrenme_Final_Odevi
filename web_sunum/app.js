// Ensure data is loaded
if (typeof presentationData === 'undefined') {
    alert("Veri yüklenemedi. Lütfen odev.py scriptini çalıştırdığınızdan emin olun.");
}

// 1. Haritayı Başlat - İstanbul merkezli
const map = L.map('map', {
    zoomControl: false
}).setView([41.0082, 28.9784], 11);

L.control.zoom({
    position: 'bottomleft'
}).addTo(map);

// Koyu tema harita katmanı
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

let currentPolylines = [];
let baseMarkers = [];
let routeMarkers = [];
let animationTimeout = null;
let animationFrameId = null;

// Durakları Haritaya Belirgin Biçimde Ekle
function initializeBaseStops() {
    presentationData.allStops.forEach(stop => {
        const marker = L.circleMarker([stop.Latitude, stop.Longitude], {
            radius: 7,
            fillColor: "#475569",
            color: "#ffffff",
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(map);
        marker.bindTooltip(stop.Durak_Adi, { direction: 'top', className: 'custom-tooltip' });
        baseMarkers.push(marker);
    });
}

function clearRoutes() {
    currentPolylines.forEach(p => map.removeLayer(p));
    routeMarkers.forEach(m => map.removeLayer(m));
    if(animationTimeout) clearTimeout(animationTimeout);
    if(animationFrameId) cancelAnimationFrame(animationFrameId);
    currentPolylines = [];
    routeMarkers = [];
}

function animateRoute(coordsArray, routeStops = []) {
    if(!coordsArray || coordsArray.length === 0) return;

    const latlngs = coordsArray.map(c => [c.lat, c.lng]);
    const start = coordsArray[0];
    const end = coordsArray[coordsArray.length - 1];

    // Ara Durakları Belirginleştirme
    routeStops.forEach((stop, index) => {
        if (index === 0 || index === routeStops.length - 1) return;
        const marker = L.circleMarker([stop.lat, stop.lng], {
            radius: 10, fillColor: "#fbbf24", color: "#000", weight: 2, fillOpacity: 1
        }).addTo(map).bindTooltip(`${index + 1}. Durak: ${stop.name}`);
        routeMarkers.push(marker);
    });

    // Başlangıç ve Bitiş Özel İşaretleri
    const startMarker = L.circleMarker([start.lat, start.lng], {
        radius: 14, fillColor: "#22c55e", color: "#fff", weight: 3, fillOpacity: 1
    }).addTo(map).bindTooltip("BAŞLANGIÇ: " + (start.name || "Start"), {permanent: false});

    const endMarker = L.circleMarker([end.lat, end.lng], {
        radius: 14, fillColor: "#ef4444", color: "#fff", weight: 3, fillOpacity: 1
    }).addTo(map).bindTooltip("BİTİŞ: " + (end.name || "End"), {permanent: false});

    routeMarkers.push(startMarker, endMarker);

    const boundsPoly = L.polyline(latlngs, {opacity: 0});
    map.flyToBounds(boundsPoly.getBounds(), { padding: [100, 100], duration: 1.5 });

    animationTimeout = setTimeout(() => {
        const antPolyline = L.polyline.antPath(latlngs, {
            delay: 600,
            dashArray: [15, 30],
            weight: 6,
            color: "#38bdf8",
            pulseColor: "#ffffff",
            paused: false
        }).addTo(map);
        currentPolylines.push(antPolyline);
    }, 1600);
}

function updateUI(modelData) {
    const conf = modelData.Confidence || 0;
    const dist = modelData.Distance || 0;
    const dur = modelData.Duration || 0;
    const acc = modelData.Accuracy || 0;
    const f1 = modelData['F1 Skoru'] || 0;
    const auc = modelData['ROC-AUC'] || 0;

    document.getElementById('val-conf').innerText = `%${conf.toFixed(2)}`;
    document.getElementById('val-dist').innerText = `${dist.toFixed(2)} km`;
    document.getElementById('val-acc').innerText = `%${acc.toFixed(2)}`;
    document.getElementById('val-f1').innerText = `%${f1.toFixed(2)}`;
    document.getElementById('val-auc').innerText = `%${auc.toFixed(2)}`;
    
    // Süre Formatlama
    if (dur > 60) {
        const h = Math.floor(dur / 60);
        const m = Math.round(dur % 60);
        document.getElementById('val-time').innerText = `${h} sa ${m} dk`;
    } else {
        document.getElementById('val-time').innerText = `${dur.toFixed(1)} dk`;
    }

    const routeList = document.getElementById('route-list');
    routeList.innerHTML = '';
    
    if(modelData.RouteCoords) {
        modelData.RouteCoords.forEach((step, index) => {
            const li = document.createElement('li');
            li.className = 'route-item';
            let bdColor = index === 0 ? 'var(--accent-green)' : (index === modelData.RouteCoords.length - 1 ? 'var(--accent-red)' : 'var(--text-muted)');
            li.style.borderLeftColor = bdColor;
            li.innerHTML = `<span class="step">${index + 1}</span> <span class="name">${step.name.substring(0, 25)}</span>`;
            routeList.appendChild(li);
        });
    }
}

async function selectModel(index) {
    if(!presentationData || !presentationData.models) return;
    const names = ['Random Forest', 'XGBoost', 'Stacking Meta-Model'];
    const modelData = presentationData.models.find(m => m.Model === names[index]);

    if(!modelData) return;

    clearRoutes();
    updateUI(modelData);

    // OSRM Gerçek Yol Entegrasyonu (Tek Parça)
    const coordsStr = modelData.RouteCoords.map(c => `${c.lng},${c.lat}`).join(';');
    const url = `http://router.project-osrm.org/route/v1/driving/${coordsStr}?geometries=geojson&overview=full`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        if(data.code === 'Ok' && data.routes && data.routes.length > 0) {
            const osrmCoords = data.routes[0].geometry.coordinates.map(c => ({lat: c[1], lng: c[0]}));
            osrmCoords[0].name = modelData.RouteCoords[0].name;
            osrmCoords[osrmCoords.length - 1].name = modelData.RouteCoords[modelData.RouteCoords.length - 1].name;
            animateRoute(osrmCoords, modelData.RouteCoords);
        } else {
            animateRoute(modelData.RouteCoords, modelData.RouteCoords);
        }
    } catch(err) {
        animateRoute(modelData.RouteCoords, modelData.RouteCoords);
    }
}

// Event Listeners
document.querySelectorAll('.model-btn').forEach((btn, idx) => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.model-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        selectModel(idx);
    });
});

// Init
try {
    initializeBaseStops();
    selectModel(0);
} catch(e) { console.error(e); }
