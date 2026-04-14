// Ensure data is loaded
if (typeof presentationData === 'undefined') {
    alert("Veri yüklenemedi. Lütfen odev.py scriptini çalıştırdığınızdan emin olun.");
}

// 1. Haritayı Başlat - İstanbul merkezli
const map = L.map('map', {
    zoomControl: false // Sağ alt köşeye taşıyacağız
}).setView([41.0082, 28.9784], 11);

L.control.zoom({
    position: 'bottomleft'
}).addTo(map);

// Koyu tema harita katmanı (CartoDB Dark Matter)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

let currentPolylines = [];
let baseMarkers = [];
let routeMarkers = []; // Start and End specific markers
let animationTimeout = null;
let animationFrameId = null;

// Tüm durakları haritaya soluk biçimde ekle
function initializeBaseStops() {
    presentationData.allStops.forEach(stop => {
        const marker = L.circleMarker([stop.Latitude, stop.Longitude], {
            radius: 6,
            fillColor: "#64748b",
            color: "#0f172a",
            weight: 2,
            opacity: 0.8,
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

    // Ara Durakları Belirginleştirme (Route Stops)
    if (routeStops && routeStops.length > 0) {
        routeStops.forEach((stop, index) => {
            // Başlangıç ve bitişi atla, o noktalara özel büyük işaret koyulacak
            if (index === 0 || index === routeStops.length - 1) return;
            
            const marker = L.circleMarker([stop.lat, stop.lng], {
                radius: 8, fillColor: "#eab308", color: "#000", weight: 2, fillOpacity: 0.95
            }).addTo(map).bindTooltip(`${index + 1}. Durak: ${stop.name}`, {permanent: false, direction: 'top'});
            routeMarkers.push(marker);
        });
    }

    // Başlangıç ve Bitiş Özel ve Daha Büyük İşaretleri
    const startMarker = L.circleMarker([start.lat, start.lng], {
        radius: 12, fillColor: "#22c55e", color: "#fff", weight: 3, fillOpacity: 1
    }).addTo(map).bindTooltip("BAŞLANGIÇ: " + start.name, {permanent: false, direction: 'right'});

    const endMarker = L.circleMarker([end.lat, end.lng], {
        radius: 12, fillColor: "#ef4444", color: "#fff", weight: 3, fillOpacity: 1
    }).addTo(map).bindTooltip("BİTİŞ: " + end.name, {permanent: false, direction: 'right'});

    routeMarkers.push(startMarker, endMarker);

    // Haritayı yumuşak bir şekilde sınırların tam ortasına al
    const boundsPoly = L.polyline(latlngs, {opacity: 0});
    map.flyToBounds(boundsPoly.getBounds(), { padding: [100, 100], duration: 1.5 });

    // FlyToBounds tamamlanana kadar bekle, sonra çizmeye başla
    animationTimeout = setTimeout(() => {
        let currentIndex = 1;
        let progress = 0;
        let startPoint = latlngs[0];
        let endPoint = latlngs[1];
        let activePoints = [latlngs[0]];

        const sequentialLine = L.polyline(activePoints, {
            color: '#3b82f6', 
            weight: 4, 
            opacity: 0.9,
            lineJoin: 'round'
        }).addTo(map);
        currentPolylines.push(sequentialLine);

        function animateFrame() {
            if (currentIndex >= latlngs.length) {
                // Rota tam çizildiğinde, AntPath (akış) görünümüne geç!
                map.removeLayer(sequentialLine);
                currentPolylines = currentPolylines.filter(p => p !== sequentialLine);

                // Rotanın tamamını soluk bir hat olarak çizelim ki genel güzergah arka planda kalsın
                const backgroundLine = L.polyline(latlngs, {
                    color: '#475569', 
                    weight: 4, 
                    opacity: 0.5
                }).addTo(map);
                currentPolylines.push(backgroundLine);

                // AntPath ile sürekli akan "gidiş" animasyonu
                const antPolyline = L.polyline.antPath(latlngs, {
                    delay: 600,            // akış hızı (ms)
                    dashArray: [15, 30],   // parça büyüklüğü ve aralığı
                    weight: 5,             // kalınlık
                    color: "#38bdf8",      // ana hat rengi
                    pulseColor: "#ffffff", // akan ışık rengi
                    paused: false,         // hareketli mi
                    reverse: false,        // gidiş yönü (start -> end)
                    hardwareAccelerated: true
                }).addTo(map);

                currentPolylines.push(antPolyline);
                return;
            }

            // OSRM aralarda binlerce detaylı nokta döndüğünden çizim hızını dinamik ayarlıyoruz
            // İzlemesi daha keyifli olması adına yaklaşık 3-4 saniye civarında bitmesi için hız çarpanı
            let speed = Math.max(0.15, latlngs.length / 180);
            progress += speed;  
            
            if (progress >= 1) {
                let stepsToAdvance = Math.floor(progress);
                // Artan suratları bir sonraki döngüye sakla
                progress -= stepsToAdvance;
                
                // Kaç nokta geçilmesi gerekiyorsa listeye ekle
                for(let i=0; i<stepsToAdvance; i++) {
                    if (currentIndex < latlngs.length) {
                        activePoints.push(latlngs[currentIndex]);
                        currentIndex++;
                    }
                }
                
                sequentialLine.setLatLngs(activePoints);
                
                if (currentIndex < latlngs.length) {
                    startPoint = latlngs[currentIndex - 1];
                    endPoint = latlngs[currentIndex];
                    animationFrameId = requestAnimationFrame(animateFrame);
                } else {
                    animationFrameId = requestAnimationFrame(animateFrame);
                }
            } else {
                // İki nokta arasını doldurarak yumuşak çizimi sağla (Linear Interpolation)
                const currentLat = startPoint[0] + (endPoint[0] - startPoint[0]) * progress;
                const currentLng = startPoint[1] + (endPoint[1] - startPoint[1]) * progress;
                
                const tempPoints = [...activePoints, [currentLat, currentLng]];
                sequentialLine.setLatLngs(tempPoints);

                animationFrameId = requestAnimationFrame(animateFrame);
            }
        }
        
        // Pürüzsüz animasyonu başlat
        animationFrameId = requestAnimationFrame(animateFrame);

    }, 1500); // map bounding bitmesini bekle
}

function updateUI(modelData) {
    // Determine metrics fields depending on Python dict structure
    const conf = modelData.Confidence || 0;
    const dist = modelData.Distance || 0;
    const acc = modelData.Accuracy || 0;
    const f1 = modelData['F1 Skoru'] || 0;
    const auc = modelData['ROC-AUC'] || 0;

    document.getElementById('val-conf').innerText = `%${conf.toFixed(2)}`;
    document.getElementById('val-dist').innerText = `${dist.toFixed(2)} km`;
    document.getElementById('val-acc').innerText = `%${acc.toFixed(2)}`;
    document.getElementById('val-f1').innerText = `%${f1.toFixed(2)}`;
    document.getElementById('val-auc').innerText = `%${auc.toFixed(2)}`;

    const routeList = document.getElementById('route-list');
    routeList.innerHTML = '';
    
    if(modelData.RouteCoords) {
        modelData.RouteCoords.forEach((step, index) => {
            const li = document.createElement('li');
            li.className = 'route-item';
            
            let bdColor = 'var(--text-muted)';
            if(index === 0) bdColor = 'var(--accent-green)';
            if(index === modelData.RouteCoords.length -1) bdColor = 'var(--accent-red)';
            li.style.borderLeftColor = bdColor;

            li.innerHTML = `<span class="step">${index + 1}</span> <span class="name">${step.name.substring(0, 25)}</span>`;
            routeList.appendChild(li);
        });
    }
}

function selectModel(index) {
    if(!presentationData || !presentationData.models) return;
    const modelData = presentationData.models.find(m => {
        if(index === 0) return m.Model === 'Random Forest';
        if(index === 1) return m.Model === 'XGBoost';
        if(index === 2) return m.Model === 'Stacking Meta-Model';
        return false;
    });

    if(!modelData) return;

    clearRoutes();
    updateUI(modelData);

    // OSRM Gerçek Yol Entegrasyonu (Real Street Routing)
    // OSRM router formatı: lon,lat;lon,lat;...
    const coordsStr = modelData.RouteCoords.map(c => `${c.lng},${c.lat}`).join(';');
    const url = `http://router.project-osrm.org/route/v1/driving/${coordsStr}?geometries=geojson&overview=full`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if(data.code === 'Ok' && data.routes && data.routes.length > 0) {
                // GeoJSON formatı lng,lat döner. Bunu bizim [lat, lng] formatına çevir
                const osrmCoords = data.routes[0].geometry.coordinates.map(c => ({lat: c[1], lng: c[0]}));
                
                // Başlangıç ve bitiş durak isimlerini tekrar ata ki animateRoute tooltip'leri çalışsın
                osrmCoords[0].name = modelData.RouteCoords[0].name;
                osrmCoords[osrmCoords.length - 1].name = modelData.RouteCoords[modelData.RouteCoords.length - 1].name;
                
                animateRoute(osrmCoords, modelData.RouteCoords);
            } else {
                console.warn("DİKKAT: OSRM servisi hatası. Doğrusal çizgilere (Haversine) geri dönülüyor.");
                animateRoute(modelData.RouteCoords, modelData.RouteCoords);
            }
        })
        .catch(err => {
            console.error("OSRM ağ hatası:", err, "Doğrusal çizgilere (Haversine) geri dönülüyor.");
            animateRoute(modelData.RouteCoords, modelData.RouteCoords);
        });
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
    // Default open first
    selectModel(0);
} catch(e) {
    console.error(e);
}
