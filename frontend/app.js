const width = 800;
const height = 600;
const nodes = new Map();
const links = [];
const edges = new Set();

const svg = d3.select('#graph').append('svg')
  .attr('width', width)
  .attr('height', height);

const linkGroup = svg.append('g');
const nodeGroup = svg.append('g');

const simulation = d3.forceSimulation()
  .force('link', d3.forceLink().id(d => d.id).distance(100))
  .force('charge', d3.forceManyBody().strength(-300))
  .force('center', d3.forceCenter(width / 2, height / 2));

function update() {
  const dataNodes = Array.from(nodes.values());
  linkGroup.selectAll('line')
    .data(links)
    .join('line');

  nodeGroup.selectAll('circle')
    .data(dataNodes)
    .join('circle')
    .attr('r', 6)
    .call(drag(simulation));

  simulation.nodes(dataNodes).on('tick', ticked);
  simulation.force('link').links(links);
  simulation.alpha(1).restart();
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
  const summaries = JSON.parse(event.data);
  summaries.forEach(summary => {
    const m = summary.match(/IP\s(\S+)\s>\s(\S+):/);
    if (!m) return;
    const src = m[1];
    const dst = m[2];
    if (!nodes.has(src)) nodes.set(src, {id: src});
    if (!nodes.has(dst)) nodes.set(dst, {id: dst});
    const key = `${src}->${dst}`;
    if (!edges.has(key)) {
      edges.add(key);
      links.push({source: nodes.get(src), target: nodes.get(dst)});
    }
  });
  update();
};
