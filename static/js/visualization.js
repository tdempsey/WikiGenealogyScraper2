/**
 * Family relationship visualization using D3.js
 */

function initializeVisualization(data) {
    const container = document.getElementById('networkContainer');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Clear any existing visualization
    container.innerHTML = '';
    
    // Create SVG element
    const svg = d3.select('#networkContainer')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Add zoom functionality
    const g = svg.append('g');
    
    svg.call(d3.zoom().on('zoom', (event) => {
        g.attr('transform', event.transform);
    }));
    
    // Define arrow markers for links
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#999')
        .style('stroke', 'none');
    
    // Create a force simulation
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50));
    
    // Create the links
    const link = g.append('g')
        .selectAll('line')
        .data(data.links)
        .enter().append('line')
        .attr('class', 'network-link')
        .attr('stroke', '#999')
        .attr('stroke-width', 1.5);
    
    // Create nodes
    const node = g.append('g')
        .selectAll('.node')
        .data(data.nodes)
        .enter().append('g')
        .attr('class', 'network-node')
        .call(drag(simulation));
    
    // Add circles to nodes
    node.append('circle')
        .attr('r', 15)
        .attr('fill', d => getNodeColor(d))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);
    
    // Add text labels to nodes
    node.append('text')
        .attr('dy', 25)
        .attr('text-anchor', 'middle')
        .text(d => d.name)
        .style('font-size', '10px')
        .style('fill', '#333');
    
    // Add tooltips
    node.append('title')
        .text(d => `${d.name} (${d.id})`);
    
    // Add interactivity
    node.on('click', function(event, d) {
        window.location.href = `/details/${d.id}`;
    });
    
    // Update positions on simulation tick
    simulation.on('tick', ticked);
    
    function getNodeColor(node) {
        switch(node.type) {
            case 'self':
                return '#3498db'; // Blue
            case 'parent':
                return '#e74c3c'; // Red
            case 'child':
                return '#2ecc71'; // Green
            case 'spouse':
                return '#f39c12'; // Orange
            case 'sibling':
                return '#9b59b6'; // Purple
            default:
                return '#95a5a6'; // Grey
        }
    }
    
    function ticked() {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('transform', d => `translate(${d.x}, ${d.y})`);
    }
}

/**
 * Create a drag behavior for nodes
 * @param {Object} simulation - The D3 force simulation
 * @returns {Object} - The drag behavior
 */
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

/**
 * Helper function to format dates in a readable way
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date (Year only)
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
        // Try to extract year from string formats like +1936-00-00T00:00:00Z
        const yearMatch = dateString.match(/[+-]?(\d{4})/);
        if (yearMatch) {
            return yearMatch[1];
        }
        return '';
    }
    
    // Just return the year
    return date.getFullYear().toString();
}