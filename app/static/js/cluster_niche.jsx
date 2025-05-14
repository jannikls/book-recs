import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const fetchNicheSpots = async (clusterId) => {
    const resp = await fetch(`/clusters/${clusterId}/niche-spots`);
    if (!resp.ok) return [];
    return await resp.json();
};

const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
        const d = payload[0].payload;
        return (
            <div style={{ background: '#fff', border: '1px solid #ccc', padding: 10 }}>
                <strong>{d.title}</strong><br />
                Author: {d.author}<br />
                Reads: {d.read_count}<br />
                Niche Score: {d.niche_score.toFixed(2)}
            </div>
        );
    }
    return null;
};

export default function ClusterNicheSpots({ clusterId }) {
    const [data, setData] = useState([]);
    useEffect(() => {
        fetchNicheSpots(clusterId).then(setData);
    }, [clusterId]);
    return (
        <ResponsiveContainer width="100%" height={400}>
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
                <XAxis dataKey="title" angle={-20} textAnchor="end" interval={0} tickFormatter={(t, i) => (
                    <span><img src={data[i]?.cover_url} alt="" style={{width:30,verticalAlign:'middle',marginRight:8}} />{t}</span>
                )} />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="niche_score" fill="#ff9800">
                    {data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill="#ff9800" />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}

// Mount to DOM if present
const root = document.getElementById('niche-spots-root');
if (root) {
    const clusterId = window.location.pathname.match(/clusters\/(\d+)/)?.[1];
    if (clusterId) {
        import('react-dom/client').then(({ createRoot }) => {
            createRoot(root).render(<ClusterNicheSpots clusterId={clusterId} />);
        });
    }
}
