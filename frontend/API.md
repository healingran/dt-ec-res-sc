# CityVisualizer 组件 API 说明

## 简介
`CityVisualizer` 是一个基于 Three.js 的 3D 城市可视化组件，封装了城市建筑、道路、设备模型、昼夜循环等核心场景，并提供外部控制接口。其他模块可通过这些接口动态改变设备颜色或高亮设备，实现数字孪生的实时交互。

## 安装与使用

### 前置依赖
- Three.js (通过 CDN 或本地安装)
- OrbitControls (Three.js 扩展)

### 引入组件
```html
<script type="importmap">
  {
    "imports": {
      "three": "https://unpkg.com/three@0.128.0/build/three.module.js",
      "three/addons/": "https://unpkg.com/three@0.128.0/examples/jsm/"
    }
  }
</script>
<script type="module">
  import { CityVisualizer } from './cityVisualizer.js';
  // 实例化
  const city = new CityVisualizer('container-id');
</script>