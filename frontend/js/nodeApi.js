/** 与后端 /nodes 相关的公共方法，供 monitor / cpu-dashboard / scene-3d 复用 */

export function getApiBase() {
    try {
        return localStorage.getItem('MONITOR_API_BASE') || 'http://127.0.0.1:8000';
    } catch {
        return 'http://127.0.0.1:8000';
    }
}

export function nodesUrl() {
    const base = getApiBase().replace(/\/$/, '');
    return `${base}/nodes`;
}

export function mapNodeId(id) {
    const n = Number(id);
    if (n === 1) return 'baseStation';
    if (n === 2) return 'camera';
    if (n === 3) return 'rsu';
    return null;
}

export function cpuBarColor(cpu) {
    if (cpu > 70) return '#e53935';
    if (cpu > 40) return '#fbc02d';
    return '#43a047';
}
