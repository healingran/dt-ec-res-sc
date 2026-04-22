import { CityVisualizer } from '../three-demo/cityVisualizer.js';
import { getApiBase, mapNodeId } from './nodeApi.js';
import * as THREE from 'three';

const echarts = window.echarts;

function apiBase() {
    return getApiBase().replace(/\/$/, '');
}

function wsDashboardUrl() {
    const base = apiBase();
    const wsBase = base.replace(/^http/, 'ws');
    return `${wsBase}/ws/dashboard`;
}

const elWs = document.getElementById('wsStatus');
const elToast = document.getElementById('toast');

function setWsStatus(mode, text) {
    if (!elWs) return;
    elWs.className = 'dash-ws dash-ws--' + mode;
    elWs.textContent = text;
}

function showToast(msg, ms = 4000) {
    if (!elToast) return;
    elToast.textContent = msg;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => {
        elToast.textContent = '';
    }, ms);
}

const visualizer = new CityVisualizer('scene3d');
// 为 dashboard 单独增加一个柔和的环境光，提升整体亮度
const extraLight = new THREE.AmbientLight(0x404060, 0.4); // 强度可调
visualizer.scene.add(extraLight);

// 可选：再加一个从顶部照射的补光
const fillLight = new THREE.PointLight(0xccaa88, 0.5);
fillLight.position.set(0, 10, 0);
visualizer.scene.add(fillLight);
const chartEl = document.getElementById('chartCompare');
const chart = echarts && chartEl
    ? echarts.init(chartEl)
    : {
        setOption() {},
        resize() {}
    };

function buildCompareOption(real, predicted) {
    if (!echarts) {
        return {};
    }
    const lr = real.length;
    const lp = predicted.length;
    const total = lr + lp;
    const xData = Array.from({ length: total }, (_, i) => String(i + 1));
    const sReal = [...real.map((v) => (v == null ? null : Number(v))), ...Array(lp).fill(null)];
    const sPred = [...Array(lr).fill(null), ...predicted.map((v) => Number(v))];

    return {
        color: ['#22d3ee', '#c084fc'],
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['真实负载 (节点1 CPU %)', '预测负载 (LSTM)'],
            bottom: 0,
            textStyle: { color: '#94a3b8', fontSize: 11 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '18%',
            top: '12%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: xData,
            axisLabel: { color: '#64748b', fontSize: 10 },
            axisLine: { lineStyle: { color: 'rgba(148,163,184,0.3)' } }
        },
        yAxis: [
            {
                type: 'value',
                name: '真实 %',
                min: 0,
                max: 100,
                nameTextStyle: { color: '#22d3ee', fontSize: 11 },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: 'rgba(51,65,85,0.35)' } }
            },
            {
                type: 'value',
                name: '预测',
                position: 'right',
                nameTextStyle: { color: '#c084fc', fontSize: 11 },
                axisLabel: { color: '#64748b' },
                splitLine: { show: false }
            }
        ],
        series: [
            {
                name: '真实负载 (节点1 CPU %)',
                type: 'line',
                yAxisIndex: 0,
                smooth: true,
                showSymbol: lr <= 24,
                data: sReal,
                lineStyle: { width: 2, color: '#22d3ee' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(34,211,238,0.25)' },
                        { offset: 1, color: 'rgba(34,211,238,0.02)' }
                    ])
                }
            },
            {
                name: '预测负载 (LSTM)',
                type: 'line',
                yAxisIndex: 1,
                smooth: true,
                showSymbol: lp <= 20,
                data: sPred,
                lineStyle: { width: 2, type: 'dashed', color: '#c084fc' }
            }
        ]
    };
}

chart.setOption(
    buildCompareOption([], []),
    { notMerge: true }
);

if (!echarts) {
    showToast('图表库加载失败：仅展示3D与实时连接状态');
}

function onDashboardPayload(payload) {
    const nodes = payload.nodes;
    const chartData = payload.chart || {};
    const real = chartData.real || [];
    const predicted = chartData.predicted || [];

    if (Array.isArray(nodes)) {
        nodes.forEach((node) => {
            const c = Number(node.cpu);
            let color;
            if (c > 70) color = 0xff0000;
            else if (c > 40) color = 0xffff00;
            else color = 0x00ff00;
            const id = mapNodeId(node.id);
            if (id) visualizer.changeNodeColor(id, color);
        });
    }

    chart.setOption(buildCompareOption(real, predicted), { notMerge: true });
}

let ws;
let reconnectTimer;
let backoffMs = 1000;
const maxBackoff = 30000;

function clearReconnect() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
}

function connectWs() {
    clearReconnect();
    const url = wsDashboardUrl();
    try {
        ws = new WebSocket(url);
    } catch (e) {
        setWsStatus('off', 'WS：创建失败');
        scheduleReconnect();
        return;
    }

    setWsStatus('wait', 'WS：连接中…');

    ws.onopen = () => {
        backoffMs = 1000;
        setWsStatus('ok', 'WS：已连接');
        if (ws._pingTimer) clearInterval(ws._pingTimer);
        ws._pingTimer = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 20000);
    };

    ws.onmessage = (ev) => {
        try {
            const data = JSON.parse(ev.data);
            onDashboardPayload(data);
        } catch (e) {
            console.error(e);
        }
    };

    ws.onerror = () => {
        setWsStatus('wait', 'WS：异常');
    };

    ws.onclose = () => {
        if (ws._pingTimer) clearInterval(ws._pingTimer);
        setWsStatus('off', 'WS：断开，重连中…');
        scheduleReconnect();
    };
}

function scheduleReconnect() {
    clearReconnect();
    const delay = backoffMs;
    backoffMs = Math.min(backoffMs * 2, maxBackoff);
    reconnectTimer = setTimeout(() => {
        connectWs();
    }, delay);
}

connectWs();

window.addEventListener('resize', () => {
    chart.resize();
});

async function postSchedule() {
    const strategy = document.getElementById('strategySelect').value;
    try {
        const res = await fetch(`${apiBase()}/schedule?strategy=${encodeURIComponent(strategy)}`, {
            method: 'POST',
            headers: { Accept: 'application/json' }
        });
        const data = await res.json();
        if (data.error) {
            showToast('调度：' + data.error);
            return;
        }
        let msg = data.message || '调度已请求';
        if (data.node_name) msg += ` → ${data.node_name}`;
        if (data.estimated_total_latency_ms != null) {
            msg += ` · 估算时延 ${data.estimated_total_latency_ms}ms`;
        }
        if (data.meet_deadline === false) {
            msg += ' · deadline 未满足';
        } else if (data.meet_deadline === true) {
            msg += ' · deadline OK';
        }
        showToast(msg);
    } catch (e) {
        showToast('调度失败：' + (e && e.message));
    }
}

async function postDemoTask() {
    try {
        const res = await fetch(`${apiBase()}/task?cpu_need=8&task_type=sensor_fusion&deadline_ms=200&data_size_kb=256`, {
            method: 'POST',
            headers: { Accept: 'application/json' }
        });
        const data = await res.json();
        showToast(data.message || '任务已添加');
    } catch (e) {
        showToast('添加任务失败：' + (e && e.message));
    }
}

document.getElementById('btnSchedule').addEventListener('click', postSchedule);
document.getElementById('btnAddTask').addEventListener('click', postDemoTask);
