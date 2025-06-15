const mapContainer = document.getElementById('map');
const width = mapContainer.clientWidth || 800;
const height = mapContainer.clientHeight || 500;

const svg = d3.select('#map').append('svg')
  .attr('width', '100%')
  .attr('height', '100%');

const graphContainer = document.getElementById('graph');
const gwidth = graphContainer.clientWidth || 400;
const gheight = graphContainer.clientHeight || 500;
const gsvg = d3.select('#graph').append('svg')
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
// Track drawn connections to avoid rendering duplicates simultaneously
const seenPairs = new Set();
const connectionTableBody = document.querySelector('#connections tbody');
const activeConnections = new Map();
const graphNodes = new Map();
let graphLinks = [];
const linkGroup = gsvg.append('g');
const nodeGroup = gsvg.append('g');
const simulation = d3.forceSimulation()
  .force('link', d3.forceLink().id(d => d.id).distance(60))
  .force('charge', d3.forceManyBody().strength(-100))
  .force('center', d3.forceCenter(gwidth / 2, gheight / 2));

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
  const pairKey = `${pkt.src}->${pkt.dst}`;
  if (seenPairs.has(pairKey)) return;
  seenPairs.add(pairKey);
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

  const line = linesGroup.append('path')
    .datum(feature)
    .attr('d', path)
    .attr('class', 'connection')
    .attr('stroke', color)
    .attr('opacity', 1);
  line.transition()
    .duration(6000)
    .attr('opacity', 0)
    .on('end', function() {
      d3.select(this).remove();
      seenPairs.delete(pairKey);
    });
}

const anomaliesEl = document.getElementById('anomalies');

function renderGraph() {
  const nodesArray = Array.from(graphNodes.values());
  const linksArray = graphLinks;

  const link = linkGroup.selectAll('line').data(linksArray);
  link.enter().append('line')
      .attr('stroke', l => colorMap[l.type] || '#f0f')
      .attr('stroke-width', 1)
    .merge(link);
  link.exit().remove();

  const node = nodeGroup.selectAll('circle').data(nodesArray, d => d.id);
  const nodeEnter = node.enter().append('circle')
      .attr('r', 5)
      .attr('class', d => d.private ? 'private' : '')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));
  nodeEnter.append('title').text(d => d.id);
  node.exit().remove();

  simulation.nodes(nodesArray).on('tick', ticked);
  simulation.force('link').links(linksArray);
  simulation.alpha(1).restart();
}

function updateGraph(pkt) {
  const s = pkt.src;
  const d = pkt.dst;
  const now = Date.now();

  if (!graphNodes.has(s)) {
    graphNodes.set(s, {id: s, private: isPrivate(s), timestamp: now});
  } else {
    graphNodes.get(s).timestamp = now;
  }
  if (!graphNodes.has(d)) {
    graphNodes.set(d, {id: d, private: isPrivate(d), timestamp: now});
  } else {
    graphNodes.get(d).timestamp = now;
  }
  graphLinks.push({source: s, target: d, type: pkt.type});
  if (graphLinks.length > 100) graphLinks.shift();

  renderGraph();
}

function ticked() {
  linkGroup.selectAll('line')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  nodeGroup.selectAll('circle')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y);
}

function dragstarted(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

function dragended(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

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

setInterval(() => {
  const now = Date.now();
  let changed = false;
  for (const [ip, node] of graphNodes.entries()) {
    if (now - node.timestamp > 30000) {
      graphNodes.delete(ip);
      graphLinks = graphLinks.filter(l => l.source !== ip && l.target !== ip);
      changed = true;
    }
  }
  if (changed) {
    renderGraph();
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
    updateGraph(pkt);
  });
  (data.anomalies || []).forEach(a => addAnomaly(a));
};
