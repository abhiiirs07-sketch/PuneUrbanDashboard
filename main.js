// ====================
// 1. Initialize GEE
// ====================
ee.initialize();

// ====================
// 2. Load your LULC Images
// ====================
var lulcImages = {
    1990: ee.Image("projects/jarvice-ng/assets/Pune_LULC_1990"),
    2000: ee.Image("projects/jarvice-ng/assets/Pune_LULC_2000"),
    2019: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20191"),
    2025: ee.Image("projects/jarvice-ng/assets/Pune_LULC_20251")
};

var yearsList = [1990, 2000, 2019, 2025];
var pixelArea = ee.Image.pixelArea();

// Pune ROI
var pune = ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.and(
        ee.Filter.eq('ADM0_NAME','India'),
        ee.Filter.eq('ADM1_NAME','Maharashtra'),
        ee.Filter.eq('ADM2_NAME','Pune')
    ));

// Urban class code
var urbanCode = 1; // change if your raster uses different code

// ====================
// 3. Leaflet Map
// ====================
var map = L.map('map').setView([18.52, 73.85], 9);

// Base layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

var currentLayer;

// ====================
// 4. Function to add Urban Layer
// ====================
function addUrbanLayer(year) {
    if (currentLayer) map.removeLayer(currentLayer);

    var urban = lulcImages[year].eq(urbanCode).selfMask().clip(pune);
    
    var visParams = {palette: ['red'], min:0, max:1};

    // Get MapID
    var mapid = ee.Image(urban).getMap(visParams);
    mapid.evaluate(function(m) {
        currentLayer = L.tileLayer(m.urlFormat, {
            attribution: 'Google Earth Engine'
        }).addTo(map);
    });

    // Calculate area
    var area = urban.multiply(pixelArea).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: pune,
        scale: 30,
        maxPixels: 1e13
    });

    area.evaluate(function(result) {
        var bandName = Object.keys(result)[0];
        var urbanArea = result[bandName]/1e6; // sq km
        document.getElementById('areaLabel').innerText = 'Year: ' + year + ' | Urban Area: ' + urbanArea.toFixed(2) + ' sq.km';
    });
}

// ====================
// 5. Dropdown Event
// ====================
document.getElementById('yearSelect').addEventListener('change', function() {
    addUrbanLayer(parseInt(this.value));
});

// Initial Layer
addUrbanLayer(2000);

// ====================
// 6. Chart (Google Charts)
// ====================
google.charts.load('current', {'packages':['corechart']});
google.charts.setOnLoadCallback(drawChart);

function drawChart() {
    var promises = yearsList.map(function(y) {
        var urban = lulcImages[y].eq(urbanCode).selfMask().clip(pune);
        var area = urban.multiply(pixelArea()).reduceRegion({
            reducer: ee.Reducer.sum(),
            geometry: pune,
            scale: 30,
            maxPixels: 1e13
        });
        return area.evaluate(function(res) {
            var band = Object.keys(res)[0];
            return [y, res[band]/1e6];
        });
    });

    Promise.all(promises).then(function(data) {
        var chartData = google.visualization.arrayToDataTable([['Year','Urban Area']].concat(data));
        var chart = new google.visualization.LineChart(document.getElementById('chart_div'));
        chart.draw(chartData, {title:'Urban Growth Trend', lineWidth:2, pointSize:5});
    });
}

// ====================
// 7. Compare 1990 vs 2025
// ====================
document.getElementById('compareBtn').addEventListener('click', function() {
    if (currentLayer) map.removeLayer(currentLayer);
    var urban1990 = lulcImages[1990].eq(urbanCode).selfMask().clip(pune);
    var urban2025 = lulcImages[2025].eq(urbanCode).selfMask().clip(pune);
    var growth = urban2025.subtract(urban1990);

    growth.getMap({palette:['yellow'], min:-1, max:1}).evaluate(function(m) {
        currentLayer = L.tileLayer(m.urlFormat).addTo(map);
    });
});

// ====================
// 8. Swipe 1990 vs 2025
// ====================
document.getElementById('swipeBtn').addEventListener('click', function() {
    var urban1990 = lulcImages[1990].eq(urbanCode).selfMask().clip(pune);
    var urban2025 = lulcImages[2025].eq(urbanCode).selfMask().clip(pune);

    urban1990.getMap({palette:['blue'], min:0, max:1}).evaluate(function(m1) {
        urban2025.getMap({palette:['red'], min:0, max:1}).evaluate(function(m2) {
            var left = L.tileLayer(m1.urlFormat);
            var right = L.tileLayer(m2.urlFormat);

            var swipeMap = L.map('map', {center:[18.52,73.85], zoom:9});
            L.control.layers({},{'1990':[left],'2025':[right]}).addTo(swipeMap);
            
            var swiper = L.control.swipe(left, right, {map: swipeMap});
            swiper.addTo(swipeMap);
        });
    });
});