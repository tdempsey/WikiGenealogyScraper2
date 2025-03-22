/**
 * Family relationship visualization using D3.js
 */

let simulation; // Store the force simulation globally

/**
 * Initialize the family relationship visualization
 * @param {Object} data - The family network data with nodes and links
 */
function initializeVisualization(data) {
    // Get the container dimensions
    const container = document.getElementById('visualization-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Clear any existing visualization
    d3.select(container).selectAll('*').remove();
    
    // Create SVG element
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height]);
    
    // Add zoom functionality
    const zoomGroup = svg.append('g');
    
    svg.call(d3.zoom()
        .extent([[0, 0], [width, height]])
        .scaleExtent([0.5, 5])
        .on('zoom', (event) => {
            zoomGroup.attr('transform', event.transform);
        }));
    
    // Create a tooltip
    const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0)
        .style('position', 'absolute')
        .style('background-color', 'white')
        .style('border', '1px solid #ddd')
        .style('padding', '10px')
        .style('border-radius', '5px')
        .style('pointer-events', 'none')
        .style('font-family', "'Source Sans Pro', sans-serif")
        .style('font-size', '14px')
        .style('box-shadow', '0 2px 5px rgba(0,0,0,0.1)');
    
    // Prepare the data
    const nodes = data.nodes;
    
    // Create link objects with source and target as objects
    const links = data.links.map(link => {
        const source = nodes.find(node => node.id === link.source);
        const target = nodes.find(node => node.id === link.target);
        return {
            source: source,
            target: target,
            type: link.type
        };
    });
    
    // Define link colors and styles by type
    const linkStyles = {
        parent: {
            color: '#2C3E50',
            dasharray: 'none',
            width: 2
        },
        child: {
            color: '#2C3E50',
            dasharray: 'none',
            width: 2
        },
        spouse: {
            color: '#3498DB',
            dasharray: '5,5',
            width: 2
        },
        sibling: {
            color: '#34495E',
            dasharray: '2,2',
            width: 1.5
        }
    };
    
    // Define node colors by gender and depth
    function getNodeColor(node) {
        // Central node is highlighted
        if (node.depth === 0) {
            return '#3498DB';
        }
        
        // Color by gender if available
        if (node.gender) {
            if (node.gender === 'male') {
                return '#7FB3D5'; // Light blue
            } else if (node.gender === 'female') {
                return '#F5B7B1'; // Light red/pink
            }
        }
        
        // Default color based on depth
        const depthColors = ['#3498DB', '#2C3E50', '#34495E', '#7F8C8D'];
        return depthColors[Math.min(node.depth, depthColors.length - 1)];
    }
    
    // Create the links
    const link = zoomGroup.append('g')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .style('stroke', d => linkStyles[d.type].color)
        .style('stroke-width', d => linkStyles[d.type].width)
        .style('stroke-dasharray', d => linkStyles[d.type].dasharray);
    
    // Create the nodes
    const node = zoomGroup.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter()
        .append('circle')
        .attr('r', d => d.depth === 0 ? 20 : 15)
        .style('fill', getNodeColor)
        .style('stroke', '#fff')
        .style('stroke-width', 2)
        .call(drag(simulation))
        .on('mouseover', function(event, d) {
            // Show tooltip
            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
                
            // Format dates
            let birthDate = d.birth_date ? formatDate(d.birth_date) : 'Unknown';
            let deathDate = d.death_date ? formatDate(d.death_date) : d.depth === 0 ? 'Present' : 'Unknown';
            
            tooltip.html(`
                <strong>${d.name}</strong><br>
                <span style="color: #666;">Birth:</span> ${birthDate}<br>
                <span style="color: #666;">Death:</span> ${deathDate}<br>
                ${d.bio ? `<em>${d.bio}</em>` : ''}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
                
            // Highlight node
            d3.select(this)
                .style('stroke', '#E74C3C')
                .style('stroke-width', 3);
                
            // Highlight connected links
            link.style('stroke-opacity', l => 
                (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.2
            );
        })
        .on('mouseout', function() {
            // Hide tooltip
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
                
            // Remove highlighting
            d3.select(this)
                .style('stroke', '#fff')
                .style('stroke-width', 2);
                
            // Reset link opacity
            link.style('stroke-opacity', 1);
        })
        .on('click', function(event, d) {
            // Navigate to person details on click
            window.location.href = `/details/${d.id}`;
        });
    
    // Add labels to nodes
    const label = zoomGroup.append('g')
        .selectAll('text')
        .data(nodes)
        .enter()
        .append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dy', 30)
        .text(d => d.name)
        .style('font-size', d => d.depth === 0 ? '14px' : '12px')
        .style('font-weight', d => d.depth === 0 ? 'bold' : 'normal');
    
    // Create force simulation
    simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links)
            .id(d => d.id)
            .distance(d => {
                // Adjust link distance based on relationship type
                if (d.type === 'spouse') return 100;
                if (d.type === 'parent' || d.type === 'child') return 120;
                if (d.type === 'sibling') return 80;
                return 150;
            })
        )
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50))
        .on('tick', ticked);
    
    // Tick function to update positions
    function ticked() {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
            
        node
            .attr('cx', d => d.x = Math.max(20, Math.min(width - 20, d.x)))
            .attr('cy', d => d.y = Math.max(20, Math.min(height - 20, d.y)));
            
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    }
    
    // Add a legend
    const legend = svg.append('g')
        .attr('transform', 'translate(20, 20)');
        
    const legendItems = [
        { type: "Central Person", color: "#3498DB", line: false },
        { type: "Male", color: "#7FB3D5", line: false },
        { type: "Female", color: "#F5B7B1", line: false },
        { type: "Parent/Child", color: linkStyles.parent.color, dasharray: linkStyles.parent.dasharray, line: true },
        { type: "Spouse", color: linkStyles.spouse.color, dasharray: linkStyles.spouse.dasharray, line: true },
        { type: "Sibling", color: linkStyles.sibling.color, dasharray: linkStyles.sibling.dasharray, line: true }
    ];
    
    legendItems.forEach((item, i) => {
        const g = legend.append('g')
            .attr('transform', `translate(0, ${i * 25})`);
            
        if (item.line) {
            // Line for relationship types
            g.append('line')
                .attr('x1', 0)
                .attr('y1', 0)
                .attr('x2', 30)
                .attr('y2', 0)
                .attr('stroke', item.color)
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', item.dasharray);
        } else {
            // Circle for person types
            g.append('circle')
                .attr('cx', 15)
                .attr('cy', 0)
                .attr('r', 8)
                .attr('fill', item.color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
        }
            
        g.append('text')
            .attr('x', 40)
            .attr('y', 5)
            .style('font-size', '12px')
            .style('font-family', "'Source Sans Pro', sans-serif")
            .text(item.type);
    });
    
    // Add instructions
    svg.append('text')
        .attr('x', 20)
        .attr('y', height - 20)
        .style('font-size', '12px')
        .style('font-family', "'Source Sans Pro', sans-serif")
        .style('fill', '#666')
        .text('Tip: Drag nodes to reposition, scroll to zoom in/out, click a person to view their details');
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
    if (!dateString) return 'Unknown';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        // Just return the year for the visualization tooltip
        return date.getFullYear().toString();
    } catch (e) {
        console.error('Error formatting date:', e);
        return dateString;
    }
}
