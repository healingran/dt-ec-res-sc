import * as THREE from 'three';
import { CityVisualizer } from '../three-demo/cityVisualizer.js';
import { nodesUrl, mapNodeId } from './nodeApi.js';

const statusEl = document.getElementById('sceneStatus');

function setStatus(ok, text) {
    if (!statusEl) return;
    statusEl.className = 'scene-status ' + (ok ? 'ok' : 'err');
    statusEl.textContent = text;
}

const visualizer = new CityVisualizer('scene3d');

// 设置默认视角为全局视角
visualizer.setView('global');   // ← 添加这一行

// 全色环颜色映射函数 (负载 0~1 -> 十六进制颜色)
function loadToColor(load) {
    const waypoints = [
        { load: 0.0, hue: 0 },     // 红
        { load: 0.2, hue: 30 },    // 橙
        { load: 0.4, hue: 60 },    // 黄
        { load: 0.6, hue: 120 },   // 绿
        { load: 0.8, hue: 240 },   // 蓝
        { load: 1.0, hue: 300 }    // 紫
    ];
    let i = 0;
    for (; i < waypoints.length - 1; i++) {
        if (load <= waypoints[i+1].load) break;
    }
    const p1 = waypoints[i];
    const p2 = waypoints[i+1];
    const t = (load - p1.load) / (p2.load - p1.load);
    const hue = p1.hue + t * (p2.hue - p1.hue);
    const color = new THREE.Color().setHSL(hue / 360, 1.0, 0.6);
    return color.getHex();
}

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
            const load = c / 100;
            const color = loadToColor(load);
            const intensity = 0.5 + load * 0.5; // 强度随负载增大 (0.5~1.0)

            const id = mapNodeId(node.id);
            if (id) visualizer.changeNodeColor(id, color, intensity);
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

// ================= 视角切换按钮绑定 =================
document.addEventListener('DOMContentLoaded', () => {
    const btnGlobal = document.getElementById('viewGlobal');
    const btnCongested = document.getElementById('viewCongested');
    const btnBest = document.getElementById('viewBest');

    if (btnGlobal) btnGlobal.onclick = () => visualizer.setView('global');
    if (btnCongested) btnCongested.onclick = () => visualizer.setView('congested');
    if (btnBest) btnBest.onclick = () => visualizer.setView('bestNode');
});