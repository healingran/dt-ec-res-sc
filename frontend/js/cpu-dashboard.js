import { nodesUrl, cpuBarColor } from './nodeApi.js';

const echarts = window.echarts;

const statusEl = document.getElementById('apiStatus');

function setStatus(ok, text) {
    if (!statusEl) return;
    statusEl.className = 'api-status ' + (ok ? 'ok' : 'err');
    statusEl.textContent = text;
}

const barChart = echarts.init(document.getElementById('barChart'));
const lineChart = echarts.init(document.getElementById('lineChart'));

/** @type {Record<string, number[]>} */
const historyMap = {};

const barOption = {
    title: { text: 'CPU 当前负载', left: 'center' },
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '6%', bottom: '14%', top: '14%', containLabel: true },
    xAxis: { type: 'category', data: [], axisLabel: { rotate: 25 } },
    yAxis: { type: 'value', min: 0, max: 100, name: '%' },
    series: [{ type: 'bar', data: [] }]
};

const lineOption = {
    title: { text: '多节点 CPU 负载变化', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', bottom: 0 },
    grid: { left: '8%', right: '6%', bottom: '18%', top: '14%', containLabel: true },
    xAxis: { type: 'category', data: [], name: '采样序号' },
    yAxis: { type: 'value', min: 0, max: 100, name: '%' },
    series: []
};

barChart.setOption(barOption);
lineChart.setOption(lineOption);

function resizeCharts() {
    barChart.resize();
    lineChart.resize();
}
window.addEventListener('resize', resizeCharts);

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
            setStatus(false, '接口返回 nodes 为空。API：' + url);
            return;
        }

        fetchCount += 1;
        const names = nodes.map((n) => n.name);
        const cpuValues = nodes.map((n) => Number(n.cpu));

        const barData = cpuValues.map((v) => ({
            value: v,
            itemStyle: { color: cpuBarColor(v) }
        }));

        barChart.setOption(
            {
                xAxis: { data: names },
                series: [{ type: 'bar', data: barData }]
            },
            { replaceMerge: ['series'] }
        );

        nodes.forEach((node) => {
            const key = node.name;
            if (!historyMap[key]) historyMap[key] = [];
            historyMap[key].push(Number(node.cpu));
            if (historyMap[key].length > 30) historyMap[key].shift();
        });

        const keys = Object.keys(historyMap);
        const sampleLen = keys.length ? historyMap[keys[0]].length : 0;
        const xLabels = Array.from({ length: sampleLen }, (_, i) => String(i + 1));

        const series = keys.map((name) => ({
            name,
            type: 'line',
            smooth: true,
            showSymbol: sampleLen <= 15,
            data: historyMap[name]
        }));

        lineChart.setOption(
            {
                legend: { data: keys },
                xAxis: { data: xLabels },
                series
            },
            { replaceMerge: ['series'] }
        );

        const snap = nodes.map((n) => `${n.name}:${n.cpu}%`).join(' · ');
        const t = new Date().toLocaleTimeString();
        setStatus(true, `第 ${fetchCount} 次拉取 ${t} | ${snap}`);

        resizeCharts();
    } catch (err) {
        const origin = typeof window !== 'undefined' ? window.location.origin : '';
        setStatus(
            false,
            `拉取失败：${err && err.message ? err.message : err} | ${url}` +
                (origin ? ` | 当前 origin：${origin}` : '')
        );
        console.error(err);
    }
}

fetchData();
setInterval(fetchData, 2000);
requestAnimationFrame(() => resizeCharts());
