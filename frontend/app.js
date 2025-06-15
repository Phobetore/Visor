const mapContainer = document.getElementById('map');
const width = mapContainer.clientWidth || 800;
const height = mapContainer.clientHeight || 500;

const svg = d3.select('#map').append('svg')
  .attr('width', '100%')
  .attr('height', '100%');

// container for definitions (currently unused but kept for future needs)
svg.append('defs');

// group used for zoom/pan transformations
const zoomGroup = svg.append('g');
// layer for the world map
const mapLayer = zoomGroup.append('g');
// layer for drawing connection lines above the map
const linesGroup = zoomGroup.append('g');

const graphContainer = document.getElementById('graph');
const gwidth = graphContainer.clientWidth || 400;
const gheight = graphContainer.clientHeight || 500;
const gsvg = d3.select('#graph').append('svg')
  .attr('width', '100%')
  .attr('height', '100%');

const sidebarEl = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggleSidebar');
if (toggleSidebarBtn) {
  toggleSidebarBtn.addEventListener('click', () => {
    sidebarEl.classList.toggle('collapsed');
  });
}

const projection = d3.geoMercator();
projection.fitSize([width, height], {type: 'Sphere'});
const path = d3.geoPath().projection(projection);

// enable zoom and pan on the map
const zoom = d3.zoom()
  .scaleExtent([1, 8])
  .on('zoom', (event) => {
    zoomGroup.attr('transform', event.transform);
  });
svg.call(zoom);

// Track drawn connections to avoid rendering duplicates simultaneously
const seenPairs = new Set();
// Maintain queues of animations per normalized host pair to play request
// and response in sequence
const animationQueues = new Map();
const connectionTableBody = document.querySelector('#connections tbody');
const activeConnections = new Map();
const graphNodes = new Map();
let graphLinks = [];
const MAX_TABLE_ROWS = 50;
const graphZoomGroup = gsvg.append('g');
const linkGroup = graphZoomGroup.append('g');
const nodeGroup = graphZoomGroup.append('g');

const graphZoom = d3.zoom()
  .scaleExtent([0.5, 5])
  .on('zoom', e => graphZoomGroup.attr('transform', e.transform));
gsvg.call(graphZoom);
const simulation = d3.forceSimulation()
  .force('link', d3.forceLink().id(d => d.id).distance(60))
  .force('charge', d3.forceManyBody().strength(-50))
  .force('center', d3.forceCenter(gwidth / 2, gheight / 2))
  .force('x', d3.forceX(gwidth / 2).strength(0.05))
  .force('y', d3.forceY(gheight / 2).strength(0.05));

d3.json('/static/js/countries-110m.json').then(world => {
  const countries = topojson.feature(world, world.objects.countries);
  mapLayer.append('path')
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
  'local-local': '#0f0',
  'local-public': '#2af',
  'public-local': '#f44',
  'public-public': '#f0f'
};

let serverPos = {lat: 0, lon: 0};

function highlightNode(ip, on) {
  nodeGroup.selectAll('circle')
    .filter(d => d.id === ip)
    .classed('highlight', on);
}

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

function animateLine(feature, color, pairKey) {
  return new Promise(resolve => {
    const line = linesGroup.append('path')
      .datum(feature)
      .attr('d', path)
      .attr('class', 'connection')
      .attr('stroke', color)
      .attr('opacity', 1);

    const length = line.node().getTotalLength();
    line
      .attr('stroke-dasharray', `${length} ${length}`)
      .attr('stroke-dashoffset', length)
      .transition()
      .duration(1000)
      .attr('stroke-dashoffset', 0)
      .transition()
      .duration(5000)
      .attr('stroke-dashoffset', -length)
      .attr('opacity', 0)
      .on('end', function() {
        d3.select(this).remove();
        seenPairs.delete(pairKey);
        resolve();
      });
  });
}

function drawConnection(pkt) {
  if (pkt.src_lat == null || pkt.dst_lat == null) return;
  const type = trafficType(pkt);
  if (!filters[type]) return;
  const pairKey = `${pkt.src}->${pkt.dst}`;
  if (seenPairs.has(pairKey)) return;
  seenPairs.add(pairKey);
  const srcCoords = isPrivate(pkt.src) ? [serverPos.lon, serverPos.lat] : [pkt.src_lon, pkt.src_lat];
  const dstCoords = isPrivate(pkt.dst) ? [serverPos.lon, serverPos.lat] : [pkt.dst_lon, pkt.dst_lat];
  const feature = {
    type: 'LineString',
    coordinates: [srcCoords, dstCoords]
  };
  let color = '#f0f';
  if (pkt.type === 'local-local') color = 'green';
  else if (pkt.type === 'local-public') color = 'blue';
  else if (pkt.type === 'public-local') color = 'red';

  const normKey = [pkt.src, pkt.dst].sort().join('->');
  const queue = animationQueues.get(normKey) || Promise.resolve();
  animationQueues.set(normKey, queue.then(() => animateLine(feature, color, pairKey)));
}

const anomaliesEl = document.getElementById('anomalies');

function renderGraph() {
  const nodesArray = Array.from(graphNodes.values());
  const linksArray = graphLinks;

  const linkKey = l => `${typeof l.source === 'object' ? l.source.id : l.source}->${typeof l.target === 'object' ? l.target.id : l.target}`;
  linkGroup.selectAll('line')
    .data(linksArray, linkKey)
    .join(
      enter => enter.append('line')
        .attr('stroke', l => colorMap[l.type] || '#f0f')
        .attr('stroke-width', 1),
      update => update.attr('stroke', l => colorMap[l.type] || '#f0f'),
      exit => exit.remove()
    );

  nodeGroup.selectAll('circle')
    .data(nodesArray, d => d.id)
    .join(
      enter => {
        const circle = enter.append('circle')
          .attr('r', 5)
          .attr('class', d => d.private ? 'private' : '')
          .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
        circle.append('title').text(d => d.id);
        return circle;
      },
      update => update,
      exit => exit.remove()
    );

  simulation.nodes(nodesArray).on('tick', ticked);
  simulation.force('link').links(linksArray);
  simulation.alphaTarget(0.2).restart();
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
    tr.dataset.src = pkt.src;
    tr.dataset.dst = pkt.dst;
    tr.addEventListener('mouseenter', () => {
      highlightNode(tr.dataset.src, true);
      highlightNode(tr.dataset.dst, true);
    });
    tr.addEventListener('mouseleave', () => {
      highlightNode(tr.dataset.src, false);
      highlightNode(tr.dataset.dst, false);
    });
    connectionTableBody.appendChild(tr);
    while (connectionTableBody.rows.length > MAX_TABLE_ROWS) {
      connectionTableBody.deleteRow(0);
    }
    rec = {tr};
    activeConnections.set(key, rec);
  } else {
    rec.tr.innerHTML = rowHtml;
    rec.tr.style.color = colorMap[pkt.type] || '#f0f';
    rec.tr.dataset.src = pkt.src;
    rec.tr.dataset.dst = pkt.dst;
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

const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${wsProto}://${location.host}/ws`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.server_location) {
    serverPos = data.server_location;
  }
  (data.packets || []).forEach(pkt => {
    drawConnection(pkt);
    updateConnection(pkt);
    updateGraph(pkt);
  });
  (data.anomalies || []).forEach(a => addAnomaly(a));
};
