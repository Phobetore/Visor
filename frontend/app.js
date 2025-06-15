const container = document.getElementById('map');
const width = container.clientWidth || 800;
const height = container.clientHeight || 500;

const svg = d3.select('#map').append('svg')
  .attr('width', '100%')
  .attr('height', '100%');

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
const seenPairs = new Set();
const connectionTableBody = document.querySelector('#connections tbody');
const activeConnections = new Map();

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

const colorMap = {
  'local-local': 'green',
  'local-public': 'blue',
  'public-local': 'red',
  'public-public': '#f0f'
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
    .attr('stroke', color)
    .attr('opacity', 1)
    .transition()
    .duration(6000)
    .attr('opacity', 0)
    .remove();
}

const anomaliesEl = document.getElementById('anomalies');

function updateConnection(pkt) {
  const key = `${pkt.src}:${pkt.src_port}->${pkt.dst}:${pkt.dst_port}:${pkt.proto}`;
  const now = Date.now();
  let rec = activeConnections.get(key);
  const rowHtml = (
    `<td><img class="flag" src="https://flagcdn.com/16x12/${(pkt.src_country_code||'').toLowerCase()}.png"> ${pkt.src}</td>`+
    `<td>→</td>`+
    `<td><img class="flag" src="https://flagcdn.com/16x12/${(pkt.dst_country_code||'').toLowerCase()}.png"> ${pkt.dst}</td>`+
    `<td>${pkt.proto}</td>`
  );
  if (!rec) {
    const tr = document.createElement('tr');
    tr.innerHTML = rowHtml;
    tr.style.color = colorMap[pkt.type] || '#f0f';
    connectionTableBody.appendChild(tr);
    rec = {tr};
    activeConnections.set(key, rec);
  } else {
    rec.tr.innerHTML = rowHtml;
    rec.tr.style.color = colorMap[pkt.type] || '#f0f';
  }
  rec.timestamp = now;
}

setInterval(() => {
  const now = Date.now();
  for (const [key, rec] of activeConnections.entries()) {
    if (now - rec.timestamp > 30000) {
      rec.tr.remove();
      activeConnections.delete(key);
    }
  }
}, 5000);

function addAnomaly(text) {
  anomaliesEl.textContent += text + '\n';
  anomaliesEl.scrollTop = anomaliesEl.scrollHeight;
}

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  (data.packets || []).forEach(pkt => {
    drawConnection(pkt);
    updateConnection(pkt);
  });
  (data.anomalies || []).forEach(a => addAnomaly(a));
};
