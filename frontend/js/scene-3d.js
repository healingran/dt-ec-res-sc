import { CityVisualizer } from '../three-demo/cityVisualizer.js';
import { nodesUrl, mapNodeId } from './nodeApi.js';

const statusEl = document.getElementById('sceneStatus');

function setStatus(ok, text) {
    if (!statusEl) return;
    statusEl.className = 'scene-status ' + (ok ? 'ok' : 'err');
    statusEl.textContent = text;
}

const visualizer = new CityVisualizer('scene3d');

let fetchCount = 0;

async function fetchData() {
    const url = nodesUrl();
    try {
        const res = await fetch(url, {
            cache: 'no-store',
            headers: { Accept: 'application/json' }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        const nodes = data.nodes;
        if (!Array.isArray(nodes) || nodes.length === 0) {
            setStatus(false, 'nodes 为空 · ' + url);
            return;
        }

        fetchCount += 1;
        nodes.forEach((node) => {
            const c = Number(node.cpu);
            let color;
            if (c > 70) color = 0xff0000;
            else if (c > 40) color = 0xffff00;
            else color = 0x00ff00;

            const id = mapNodeId(node.id);
            if (id) visualizer.changeNodeColor(id, color);
        });

        const snap = nodes.map((n) => `${n.name}:${n.cpu}%`).join(' · ');
        setStatus(true, `第 ${fetchCount} 次同步 · ${snap}`);
    } catch (err) {
        const origin = typeof window !== 'undefined' ? window.location.origin : '';
        setStatus(
            false,
            `数据同步失败：${err && err.message ? err.message : err}` + (origin ? ` · ${origin}` : '')
        );
        console.error(err);
    }
}

fetchData();
setInterval(fetchData, 2000);
