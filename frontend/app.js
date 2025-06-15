const width = 800;
const height = 600;
const nodes = new Map();
const links = [];
const edges = new Map();

const svg = d3.select('#graph').append('svg')
  .attr('width', width)
  .attr('height', height);

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

const linkGroup = svg.append('g');
const nodeGroup = svg.append('g');

const simulation = d3.forceSimulation()
  .force('link', d3.forceLink().id(d => d.id).distance(100))
  .force('charge', d3.forceManyBody().strength(-100))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('x', d3.forceX(width / 2).strength(0.05))
  .force('y', d3.forceY(height / 2).strength(0.05));

function update() {
  const dataNodes = Array.from(nodes.values());
  const linkSel = linkGroup.selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke-width', d => Math.min(5, 1 + Math.log(d.count)));
  linkSel.selectAll('title').data(d => [d]).join('title').text(d => `${d.source.id} -> ${d.target.id} (${d.count})`);

  const nodeEnter = nodeGroup.selectAll('g')
    .data(dataNodes)
    .join(enter => {
      const g = enter.append('g')
        .call(drag(simulation));
      g.append('circle')
        .attr('r', 6);
      g.append('text')
        .attr('class', 'label')
        .attr('x', 8)
        .attr('y', 3)
        .text(d => d.id);
      g.on('click', (_, d) => showNodeInfo(d));
      return g;
    });
  nodeEnter.select('circle')
    .attr('class', d => d.type === 'private' ? 'private' : null)
    .attr('fill', d => d.type === 'private' ? '#0f0' : '#0ff');
  nodeEnter.selectAll('title').data(d => [d]).join('title').text(d => d.id);

  simulation.nodes(dataNodes).on('tick', ticked);
  simulation.force('link').links(links);
  simulation.alpha(0.3).restart();
}

function ticked() {
  linkGroup.selectAll('line')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);
  nodeGroup.selectAll('g')
    .attr('transform', d => `translate(${d.x},${d.y})`);
}

function drag(simulation) {
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }

  return d3.drag()
    .on('start', dragstarted)
    .on('drag', dragged)
    .on('end', dragended);
}

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (event) => {
  const packets = JSON.parse(event.data);
  packets.forEach(pkt => {
    const src = pkt.src;
    const dst = pkt.dst;
    if (!src || !dst) return;
    if (!nodes.has(src)) nodes.set(src, {id: src, type: isPrivate(src) ? 'private' : 'public'});
    if (!nodes.has(dst)) nodes.set(dst, {id: dst, type: isPrivate(dst) ? 'private' : 'public'});
    const key = `${src}->${dst}`;
    if (edges.has(key)) {
      edges.get(key).count += 1;
    } else {
      const link = {source: nodes.get(src), target: nodes.get(dst), count: 1};
      edges.set(key, link);
      links.push(link);
    }
  });
  update();
};

function isPrivate(ip) {
  return ip.startsWith('10.') ||
         ip.startsWith('192.168.') ||
         /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(ip);
}

const infoEl = document.getElementById('nodeInfo');

function showNodeInfo(node) {
  const outgoing = links.filter(l => l.source.id === node.id).map(l => l.target.id);
  const incoming = links.filter(l => l.target.id === node.id).map(l => l.source.id);
  infoEl.textContent = `IP: ${node.id}\nSortant: ${outgoing.join(', ')}\nEntrant: ${incoming.join(', ')}`;
}
