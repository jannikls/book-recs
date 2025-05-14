import React, { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

const fetchNetwork = async (clusterId) => {
    const resp = await fetch(`/clusters/${clusterId}/network`);
    if (!resp.ok) return { nodes: [], edges: [] };
    return await resp.json();
};

export default function ClusterNetwork({ clusterId }) {
    const [data, setData] = useState({ nodes: [], edges: [] });
    const fgRef = useRef();
    useEffect(() => {
        fetchNetwork(clusterId).then(setData);
    }, [clusterId]);
    return (
        <div style={{ width: "100%", height: 600 }}>
            <ForceGraph2D
                ref={fgRef}
                graphData={{ nodes: data.nodes, links: data.edges }}
                nodeLabel={node => `${node.title} (Niche: ${node.niche_score?.toFixed(2)})`}
                nodeAutoColorBy="niche_score"
                nodeVal={node => 5 + 20 * (node.niche_score || 0)}
                linkWidth={link => 2}
                linkColor={() => "#888"}
                nodeCanvasObject={(node, ctx, globalScale) => {
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, 5 + 20 * (node.niche_score || 0), 0, 2 * Math.PI, false);
                    ctx.fillStyle = node.color || "#ff9800";
                    ctx.fill();
                    ctx.font = `${12/globalScale}px Sans-Serif`;
                    ctx.textAlign = "center";
                    ctx.fillStyle = "#333";
                    ctx.fillText(node.title, node.x, node.y + 18/globalScale);
                }}
            />
        </div>
    );
}

// Mount to DOM if present
const root = document.getElementById('cluster-network-root');
if (root) {
    const clusterId = window.location.pathname.match(/clusters\/(\d+)/)?.[1];
    if (clusterId) {
        import('react-dom/client').then(({ createRoot }) => {
            createRoot(root).render(<ClusterNetwork clusterId={clusterId} />);
        });
    }
}
