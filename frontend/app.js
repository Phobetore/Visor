const width = 800;
const height = 500;

const svg = d3.select('#map').append('svg')
  .attr('width', width)
  .attr('height', height);

const projection = d3.geoMercator().scale(130).translate([width / 2, height / 1.5]);
const path = d3.geoPath().projection(projection);

svg.append('defs').append('marker')
  .attr('id', 'arrow')
  .attr('viewBox', '0 -5 10 10')
  .attr('refX', 10)
  .attr('refY', 0)
  .attr('markerWidth', 6)
  .attr('markerHeight', 6)
  .attr('orient', 'auto')
  .append('path')
  .attr('d', 'M0,-5L10,0L0,5')
  .attr('fill', '#f0f');

const linesGroup = svg.append('g');

d3.json('/static/js/countries-110m.json').then(world => {
  const countries = topojson.feature(world, world.objects.countries);
  svg.append('path')
    .datum(countries)
    .attr('d', path)
    .attr('fill', '#111')
    .attr('stroke', '#555');
});

// Traffic filter state
const filters = {
  'private-private': true,
  'private-public': true,
  'public-private': true,
  'public-public': true
};

// Initialize checkbox listeners
document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
  filters[cb.id] = cb.checked;
  cb.addEventListener('change', () => {
    filters[cb.id] = cb.checked;
  });
});

function isPrivate(ip) {
  return /^10\./.test(ip) ||
         /^192\.168\./.test(ip) ||
         /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(ip);
}

function trafficType(pkt) {
  const srcPriv = isPrivate(pkt.src);
  const dstPriv = isPrivate(pkt.dst);
  if (srcPriv && dstPriv) return 'private-private';
  if (srcPriv && !dstPriv) return 'private-public';
  if (!srcPriv && dstPriv) return 'public-private';
  return 'public-public';
}

function drawConnection(pkt) {
  if (pkt.src_lat == null || pkt.dst_lat == null) return;
  const type = trafficType(pkt);
  if (!filters[type]) return;
  const feature = {
    type: 'LineString',
    coordinates: [
      [pkt.src_lon, pkt.src_lat],
      [pkt.dst_lon, pkt.dst_lat]
    ]
  };
  let color = '#f0f';
  if (pkt.type === 'local-local') color = 'green';
  else if (pkt.type === 'local-public') color = 'blue';
  else if (pkt.type === 'public-local') color = 'red';

  linesGroup.append('path')
    .datum(feature)
    .attr('d', path)
    .attr('class', 'connection')
    .attr('stroke', color);
}

const logsEl = document.getElementById('logs');
const anomaliesEl = document.getElementById('anomalies');

function addLog(text) {
  logsEl.textContent += text + '\n';
  logsEl.scrollTop = logsEl.scrollHeight;
}

function addAnomaly(text) {
  anomaliesEl.textContent += text + '\n';
  anomaliesEl.scrollTop = anomaliesEl.scrollHeight;
}

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  (data.packets || []).forEach(pkt => {
    drawConnection(pkt);
    addLog(`${pkt.src} -> ${pkt.dst}`);
  });
  (data.anomalies || []).forEach(a => addAnomaly(a));
};
