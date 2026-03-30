import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class CityVisualizer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`Container #${containerId} not found`);

        // 配置项（可自定义）
        this.options = {
            groundSize: 90,
            ...options
        };

        // Three.js 核心对象
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        // 场景元素
        this.buildings = [];
        this.devices = [];     // 存储设备对象（含 userData.id）
        this.streetLamps = [];

        // 昼夜循环相关
        this.timeOfDay = 12;
        this.cycleSpeed = 0.003;
        this.sunLight = null;
        this.ambientLight = null;
        this.fillLight = null;
        this.stars = null;
        this.moon = null;

        // 贴图（需在外部加载或内部加载）
        this.textureLoader = new THREE.TextureLoader();

        // 初始化
        this.init();
    }

    // 初始化场景
    init() {
        // 1. 场景、相机、渲染器
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a1030);
        this.scene.fog = new THREE.FogExp2(0x0a1030, 0.006);

        this.camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
        this.camera.position.set(22, 14, 22);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // 轨道控制
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        this.controls.target.set(0, 3, 0);

        // 2. 光源系统
        this.setupLights();

        // 3. 地面（带纹理）
        this.createGround();

        // 4. 草地平面
        this.createGrass();

        // 5. 城市建筑（街区式分布）
        this.createBuildings();

        // 6. 道路模型
        this.createRoads();

        // 7. 设备模型
        this.createDevices();

        // 8. 路灯（装饰）
        this.createStreetLamps();

        // 9. 昼夜循环辅助元素（星星、月亮）
        this.createStarsAndMoon();

        // 10. 启动动画循环
        this.animate();
    }

    // 设置光源（太阳、环境光、补光）
    setupLights() {
        // 太阳（方向光）
        this.sunLight = new THREE.DirectionalLight(0xffeedd, 1.2);
        this.sunLight.position.set(10, 20, 5);
        this.sunLight.castShadow = true;
        this.sunLight.shadow.mapSize.width = 1024;
        this.sunLight.shadow.mapSize.height = 1024;
        this.sunLight.shadow.camera.near = 0.5;
        this.sunLight.shadow.camera.far = 50;
        this.sunLight.shadow.camera.left = -15;
        this.sunLight.shadow.camera.right = 15;
        this.sunLight.shadow.camera.top = 15;
        this.sunLight.shadow.camera.bottom = -15;
        this.scene.add(this.sunLight);

        // 环境光
        this.ambientLight = new THREE.AmbientLight(0x404060, 0.7);
        this.scene.add(this.ambientLight);

        // 辅助背光
        this.fillLight = new THREE.PointLight(0xffaa66, 0.5);
        this.fillLight.position.set(-8, 8, -10);
        this.scene.add(this.fillLight);
    }

    // 地面（带道路纹理）
    createGround() {
        const groundSize = this.options.groundSize;
        const groundGeometry = new THREE.PlaneGeometry(groundSize, groundSize);
        // 生成地面纹理（与之前相同，可简化）
        const canvasGround = document.createElement('canvas');
        canvasGround.width = 2048;
        canvasGround.height = 2048;
        const ctxGround = canvasGround.getContext('2d');
        ctxGround.fillStyle = '#3a6b3a';
        ctxGround.fillRect(0, 0, canvasGround.width, canvasGround.height);
        const roadWidth = 40;
        const roadColor = '#4a4a4a';
        ctxGround.fillStyle = roadColor;
        const gridSpacing = 180;
        for (let x = 0; x <= canvasGround.width; x += gridSpacing) {
            ctxGround.fillRect(x - roadWidth/2, 0, roadWidth, canvasGround.height);
            ctxGround.fillRect(0, x - roadWidth/2, canvasGround.width, roadWidth);
        }
        ctxGround.fillStyle = '#dddddd';
        const crossSize = 50;
        for (let x = 0; x <= canvasGround.width; x += gridSpacing) {
            for (let y = 0; y <= canvasGround.height; y += gridSpacing) {
                ctxGround.fillRect(x - crossSize/2, y - crossSize/2, crossSize, crossSize);
            }
        }
        ctxGround.fillStyle = '#5b8c5b';
        for (let i = 0; i < 300; i++) {
            const rx = Math.random() * canvasGround.width;
            const ry = Math.random() * canvasGround.height;
            const radius = 15 + Math.random() * 25;
            ctxGround.beginPath();
            ctxGround.arc(rx, ry, radius, 0, Math.PI*2);
            ctxGround.fill();
        }
        const groundTexture = new THREE.CanvasTexture(canvasGround);
        groundTexture.wrapS = THREE.RepeatWrapping;
        groundTexture.wrapT = THREE.RepeatWrapping;
        groundTexture.repeat.set(2, 2);
        const groundMaterial = new THREE.MeshStandardMaterial({ map: groundTexture, roughness: 0.9, metalness: 0.1 });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.2;
        ground.receiveShadow = true;
        this.scene.add(ground);
    }

    // 草地平面（使用专业贴图，路径请确保正确）
    createGrass() {
        const groundSize = this.options.groundSize;
        const grassSize = groundSize - 2;
        const grassGeometry = new THREE.PlaneGeometry(grassSize, grassSize);
        // 加载贴图（需要你的 textures 文件夹内有以下文件）
        const grassColorMap = this.textureLoader.load('textures/Grass005_1K-JPG_Color.jpg');
        const grassNormalMap = this.textureLoader.load('textures/Grass005_1K-JPG_NormalGL.jpg');
        const grassRoughnessMap = this.textureLoader.load('textures/Grass005_1K-JPG_Roughness.jpg');
        grassColorMap.wrapS = THREE.RepeatWrapping;
        grassColorMap.wrapT = THREE.RepeatWrapping;
        grassColorMap.repeat.set(4, 4);
        grassNormalMap.wrapS = THREE.RepeatWrapping;
        grassNormalMap.wrapT = THREE.RepeatWrapping;
        grassNormalMap.repeat.set(4, 4);
        grassRoughnessMap.wrapS = THREE.RepeatWrapping;
        grassRoughnessMap.wrapT = THREE.RepeatWrapping;
        grassRoughnessMap.repeat.set(4, 4);
        const grassMaterial = new THREE.MeshStandardMaterial({
            map: grassColorMap,
            normalMap: grassNormalMap,
            roughnessMap: grassRoughnessMap,
            roughness: 0.9,
            metalness: 0.1
        });
        const grassPlane = new THREE.Mesh(grassGeometry, grassMaterial);
        grassPlane.rotation.x = -Math.PI / 2;
        grassPlane.position.y = -0.1;
        grassPlane.receiveShadow = true;
        this.scene.add(grassPlane);
    }

    // 街区式建筑分布（使用外墙贴图）
    createBuildings() {
        const blockSize = 14;
        const buildingSpacing = 2.8;
        const buildingsPerBlock = 9;
        const blocks = [];
        for (let i = -3; i <= 3; i++) {
            for (let j = -3; j <= 3; j++) {
                if (Math.abs(i) <= 1 && Math.abs(j) <= 1) continue;
                blocks.push({ x: i * blockSize, z: j * blockSize });
            }
        }

        // 加载外墙贴图
        const facadeColorMap = this.textureLoader.load('textures/Facade001_1K-JPG_Color.jpg');
        const facadeNormalMap = this.textureLoader.load('textures/Facade001_1K-JPG_NormalGL.jpg');
        const facadeRoughnessMap = this.textureLoader.load('textures/Facade001_1K-JPG_Roughness.jpg');
        facadeColorMap.wrapS = THREE.RepeatWrapping;
        facadeColorMap.wrapT = THREE.RepeatWrapping;
        facadeNormalMap.wrapS = THREE.RepeatWrapping;
        facadeNormalMap.wrapT = THREE.RepeatWrapping;
        facadeRoughnessMap.wrapS = THREE.RepeatWrapping;
        facadeRoughnessMap.wrapT = THREE.RepeatWrapping;

        blocks.forEach(block => {
            for (let k = 0; k < buildingsPerBlock; k++) {
                const offsetX = (Math.random() - 0.5) * (blockSize - buildingSpacing);
                const offsetZ = (Math.random() - 0.5) * (blockSize - buildingSpacing);
                let x = block.x + offsetX;
                let z = block.z + offsetZ;
                // 避免重叠
                let overlap = false;
                for (let b of this.buildings) {
                    if (Math.hypot(b.userData.x - x, b.userData.z - z) < 1.2) {
                        overlap = true;
                        break;
                    }
                }
                if (overlap) continue;
                const height = 3 + Math.random() * 15;
                const width = 0.8 + Math.random() * 1.2;
                const depth = 0.8 + Math.random() * 1.2;
                const geometry = new THREE.BoxGeometry(width, height, depth);
                const repeatX = Math.max(1, Math.floor(width * 1.5));
                const repeatY = Math.max(2, Math.floor(height * 2.0));
                facadeColorMap.repeat.set(repeatX, repeatY);
                facadeNormalMap.repeat.set(repeatX, repeatY);
                facadeRoughnessMap.repeat.set(repeatX, repeatY);
                const material = new THREE.MeshStandardMaterial({
                    map: facadeColorMap,
                    normalMap: facadeNormalMap,
                    roughnessMap: facadeRoughnessMap,
                    roughness: 0.6,
                    metalness: 0.2,
                    color: 0xffffff
                });
                const building = new THREE.Mesh(geometry, material);
                building.position.set(x, height/2, z);
                building.castShadow = true;
                building.receiveShadow = true;
                building.userData = { x, z };
                this.scene.add(building);
                this.buildings.push(building);
            }
        });

        // 地标塔楼（单独材质）
        const towerPositions = [
            [-18, -18], [18, -18], [-18, 18], [18, 18],
            [-22, 0], [22, 0], [0, -22], [0, 22]
        ];
        const towerMat = new THREE.MeshStandardMaterial({
            color: 0x88aaff,
            metalness: 0.9,
            roughness: 0.3,
            emissive: 0x224466,
            emissiveIntensity: 0.2
        });
        towerPositions.forEach(pos => {
            const [x, z] = pos;
            const height = 20 + Math.random() * 8;
            const geometry = new THREE.BoxGeometry(1.5, height, 1.5);
            const tower = new THREE.Mesh(geometry, towerMat);
            tower.position.set(x, height/2, z);
            tower.castShadow = true;
            this.scene.add(tower);
            this.buildings.push(tower);
        });
    }

    // 道路模型（使用贴图）
    createRoads() {
        const blockSize = 14;
        // 获取街区中心点（与建筑生成时一致）
        const blocks = [];
        for (let i = -3; i <= 3; i++) {
            for (let j = -3; j <= 3; j++) {
                if (Math.abs(i) <= 1 && Math.abs(j) <= 1) continue;
                blocks.push({ x: i * blockSize, z: j * blockSize });
            }
        }

        // 加载道路贴图
        const roadColorMap = this.textureLoader.load('textures/Road008B_1K-JPG_Color.jpg');
        const roadNormalMap = this.textureLoader.load('textures/Road008B_1K-JPG_NormalGL.jpg');
        const roadRoughnessMap = this.textureLoader.load('textures/Road008B_1K-JPG_Roughness.jpg');
        roadColorMap.wrapS = THREE.RepeatWrapping;
        roadColorMap.wrapT = THREE.RepeatWrapping;
        roadColorMap.repeat.set(2, 2);
        roadNormalMap.wrapS = THREE.RepeatWrapping;
        roadNormalMap.wrapT = THREE.RepeatWrapping;
        roadNormalMap.repeat.set(2, 2);
        roadRoughnessMap.wrapS = THREE.RepeatWrapping;
        roadRoughnessMap.wrapT = THREE.RepeatWrapping;
        roadRoughnessMap.repeat.set(2, 2);
        const roadMaterial = new THREE.MeshStandardMaterial({
            map: roadColorMap,
            normalMap: roadNormalMap,
            roughnessMap: roadRoughnessMap,
            roughness: 0.7,
            metalness: 0.1
        });

        const roadModelWidth = 1.5;
        const uniqueX = [...new Set(blocks.map(b => b.x))];
        const uniqueZ = [...new Set(blocks.map(b => b.z))];
        uniqueX.forEach(x => {
            const zMin = Math.min(...blocks.filter(b => b.x === x).map(b => b.z));
            const zMax = Math.max(...blocks.filter(b => b.x === x).map(b => b.z));
            const roadLength = Math.abs(zMax - zMin) + blockSize;
            const roadGeo = new THREE.BoxGeometry(roadModelWidth, 0.1, roadLength);
            const road = new THREE.Mesh(roadGeo, roadMaterial);
            road.position.set(x, -0.08, (zMin + zMax) / 2);
            road.receiveShadow = true;
            this.scene.add(road);
        });
        uniqueZ.forEach(z => {
            const xMin = Math.min(...blocks.filter(b => b.z === z).map(b => b.x));
            const xMax = Math.max(...blocks.filter(b => b.z === z).map(b => b.x));
            const roadLength = Math.abs(xMax - xMin) + blockSize;
            const roadGeo = new THREE.BoxGeometry(roadLength, 0.1, roadModelWidth);
            const road = new THREE.Mesh(roadGeo, roadMaterial);
            road.position.set((xMin + xMax) / 2, -0.08, z);
            road.receiveShadow = true;
            this.scene.add(road);
        });
    }

    // 设备模型（基站、摄像头、路侧单元）
    createDevices() {
        // 基站
        const baseStation = new THREE.Group();
        baseStation.userData = { id: 'baseStation' };
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x4477aa, metalness: 0.7, roughness: 0.4 });
        const body = new THREE.Mesh(new THREE.BoxGeometry(1.2, 2.2, 1.2), bodyMat);
        body.position.y = 1.1;
        body.castShadow = true;
        baseStation.add(body);
        const antennaMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
        const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 1.2), antennaMat);
        antenna.position.set(0, 2.3, 0);
        antenna.castShadow = true;
        baseStation.add(antenna);
        const topMat = new THREE.MeshStandardMaterial({ color: 0xffaa66, emissive: 0xff4422, emissiveIntensity: 0.5 });
        const topSphere = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8), topMat);
        topSphere.position.set(0, 2.9, 0);
        baseStation.add(topSphere);
        baseStation.position.set(-11, 0, -9);
        baseStation.castShadow = true;
        this.scene.add(baseStation);
        this.devices.push(baseStation);

        // 摄像头
        const cameraGroup = new THREE.Group();
        cameraGroup.userData = { id: 'camera' };
        const camBodyMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.6 });
        const camBody = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.7, 1.4), camBodyMat);
        camBody.position.y = 0.35;
        camBody.castShadow = true;
        cameraGroup.add(camBody);
        const lensMat = new THREE.MeshStandardMaterial({ color: 0x88aaff, emissive: 0x2266aa, emissiveIntensity: 0.4 });
        const lens = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16), lensMat);
        lens.position.set(0, 0.35, 0.8);
        lens.castShadow = true;
        cameraGroup.add(lens);
        const standMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa });
        const stand = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.6), standMat);
        stand.position.set(0, -0.2, 0);
        stand.castShadow = true;
        cameraGroup.add(stand);
        cameraGroup.position.set(9, 0.7, 7);
        cameraGroup.rotation.y = -0.5;
        this.scene.add(cameraGroup);
        this.devices.push(cameraGroup);

        // 路侧单元 (RSU)
        const rsuGroup = new THREE.Group();
        rsuGroup.userData = { id: 'rsu' };
        const poleMat = new THREE.MeshStandardMaterial({ color: 0x888888 });
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.25, 2.5), poleMat);
        pole.position.y = 1.25;
        pole.castShadow = true;
        rsuGroup.add(pole);
        const armMat = new THREE.MeshStandardMaterial({ color: 0x2266aa });
        const arm = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.15, 0.3), armMat);
        arm.position.set(0, 2.6, 0);
        arm.castShadow = true;
        rsuGroup.add(arm);
        const boxMat = new THREE.MeshStandardMaterial({ color: 0x44aaff, emissive: 0x004466, emissiveIntensity: 0.3 });
        const box = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.5), boxMat);
        box.position.set(0, 2.9, 0);
        box.castShadow = true;
        rsuGroup.add(box);
        rsuGroup.position.set(4, 0, -10);
        this.scene.add(rsuGroup);
        this.devices.push(rsuGroup);
    }

    // 路灯
    createStreetLamps() {
        const lampMatBody = new THREE.MeshStandardMaterial({ color: 0xccaa77, metalness: 0.5 });
        const lampMatLight = new THREE.MeshStandardMaterial({ color: 0xffaa66, emissive: 0xff4422, emissiveIntensity: 0.6 });
        for (let i = 0; i < 40; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = 16 + Math.random() * 14;
            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;
            const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.3, 2.5, 6), lampMatBody);
            pole.position.set(x, 1.25, z);
            pole.castShadow = true;
            this.scene.add(pole);
            const lampSphere = new THREE.Mesh(new THREE.SphereGeometry(0.28, 8), lampMatLight);
            lampSphere.position.set(x, 2.6, z);
            lampSphere.castShadow = true;
            this.scene.add(lampSphere);
            this.streetLamps.push(lampSphere);
        }
    }

    // 星星和月亮
    createStarsAndMoon() {
        const starGeometry = new THREE.BufferGeometry();
        const starCount = 1200;
        const starPositions = new Float32Array(starCount * 3);
        for (let i = 0; i < starCount; i++) {
            starPositions[i*3] = (Math.random() - 0.5) * 200;
            starPositions[i*3+1] = (Math.random() - 0.5) * 40 + 20;
            starPositions[i*3+2] = (Math.random() - 0.5) * 120 - 60;
        }
        starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
        const starMaterial = new THREE.PointsMaterial({ color: 0xffffff, size: 0.2, transparent: true, opacity: 0 });
        this.stars = new THREE.Points(starGeometry, starMaterial);
        this.scene.add(this.stars);

        const moonMat = new THREE.MeshStandardMaterial({ color: 0xdddddd, emissive: 0x444444 });
        this.moon = new THREE.Mesh(new THREE.SphereGeometry(0.8, 32, 32), moonMat);
        this.scene.add(this.moon);
    }

    // 昼夜循环更新（在动画中调用）
    updateDayNightCycle() {
        this.timeOfDay += this.cycleSpeed;
        if (this.timeOfDay >= 24) this.timeOfDay -= 24;
        const angleRad = (this.timeOfDay / 24) * Math.PI * 2;
        const sunHeight = Math.sin(angleRad);
        const sunX = Math.cos(angleRad) * 28;
        const sunZ = Math.sin(angleRad) * 28;
        const sunY = Math.max(0, sunHeight * 22);
        this.sunLight.position.set(sunX, sunY + 5, sunZ);

        const intensityFactor = Math.max(0, Math.sin(angleRad) * 1.2);
        this.sunLight.intensity = Math.min(1.5, intensityFactor * 1.5);
        this.ambientLight.intensity = 0.7 + intensityFactor * 0.45;
        this.fillLight.intensity = 0.3 + (1 - intensityFactor) * 0.4;

        const skyColor = new THREE.Color().setHSL(0.58, 0.7, 0.2 + intensityFactor * 0.3);
        this.scene.background = skyColor;
        this.scene.fog.color = skyColor;

        const starOpacity = Math.max(0, 1 - intensityFactor * 1.5);
        this.stars.material.opacity = starOpacity;

        const moonAngle = angleRad + Math.PI;
        const moonX = Math.cos(moonAngle) * 35;
        const moonZ = Math.sin(moonAngle) * 35;
        const moonY = Math.sin(moonAngle) * 18;
        this.moon.position.set(moonX, moonY, moonZ);

        const nightFactor = 1 - intensityFactor;
        this.streetLamps.forEach(lamp => {
            if (lamp.material) lamp.material.emissiveIntensity = 0.3 + nightFactor * 0.7;
        });
        // 建筑自发光强度（如有需要）
        this.buildings.forEach(building => {
            if (building.material) {
                building.material.emissiveIntensity = 0.15 + nightFactor * 0.4;
            }
        });
        // 设备顶部灯球发光
        this.devices.forEach(device => {
            device.traverse(child => {
                if (child.isMesh && child.material && child.material.emissiveIntensity !== undefined) {
                    child.material.emissiveIntensity = 0.3 + nightFactor * 0.6;
                }
            });
        });

        if (intensityFactor < 0.3) {
            this.sunLight.color.setHex(0xffaa77);
        } else if (intensityFactor > 0.7) {
            this.sunLight.color.setHex(0xfff5e0);
        } else {
            this.sunLight.color.setHex(0xffddbb);
        }
    }

    // 公共接口：改变设备颜色
    changeNodeColor(nodeId, color) {
        const device = this.devices.find(d => d.userData.id === nodeId);
        if (!device) {
            console.warn(`Device ${nodeId} not found`);
            return;
        }
        device.traverse(child => {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(mat => mat.color.set(color));
                } else {
                    child.material.color.set(color);
                }
            }
        });
    }

    /**
     * 高亮指定设备（增加自发光强度并改变自发光颜色）
     * @param {string} nodeId - 设备标识符 ('baseStation', 'camera', 'rsu')
     * @param {number} intensity - 高亮强度（0~1），默认为 1
     * @param {number|string} color - 高亮颜色，默认为 0xffaa00（橙色）
     */
    highlightNode(nodeId, intensity = 1, color = 0xffaa00) {
        const device = this.devices.find(d => d.userData.id === nodeId);
        if (!device) {
            console.warn(`Device ${nodeId} not found`);
            return;
        }

        // 保存原始自发光状态（仅首次）
        if (!device.userData.originalEmissive) {
            device.userData.originalEmissive = [];
            device.userData.originalEmissiveIntensity = [];
            device.traverse(child => {
                if (child.isMesh && child.material) {
                    const materials = Array.isArray(child.material) ? child.material : [child.material];
                    materials.forEach(mat => {
                        device.userData.originalEmissive.push(mat.emissive ? mat.emissive.clone() : new THREE.Color(0x000000));
                        device.userData.originalEmissiveIntensity.push(mat.emissiveIntensity || 0);
                    });
                }
            });
        }

        // 应用高亮：设置自发光颜色和强度
        let idx = 0;
        device.traverse(child => {
            if (child.isMesh && child.material) {
                const materials = Array.isArray(child.material) ? child.material : [child.material];
                materials.forEach(mat => {
                    if (mat.emissive) {
                        mat.emissive.set(color);
                        mat.emissiveIntensity = intensity;
                    }
                    idx++;
                });
            }
        });
    }

    /**
     * 清除高亮，恢复原始自发光状态
     * @param {string} nodeId - 设备标识符
     */
    clearHighlight(nodeId) {
        const device = this.devices.find(d => d.userData.id === nodeId);
        if (!device || !device.userData.originalEmissive) return;

        let idx = 0;
        device.traverse(child => {
            if (child.isMesh && child.material) {
                const materials = Array.isArray(child.material) ? child.material : [child.material];
                materials.forEach(mat => {
                    if (mat.emissive && device.userData.originalEmissive[idx]) {
                        mat.emissive.copy(device.userData.originalEmissive[idx]);
                        mat.emissiveIntensity = device.userData.originalEmissiveIntensity[idx];
                    }
                    idx++;
                });
            }
        });
    }

    // 动画循环
    animate() {
        requestAnimationFrame(() => this.animate());
        this.updateDayNightCycle();
        // 摄像头缓慢转动（如有）
        const cameraDevice = this.devices.find(d => d.userData.id === 'camera');
        if (cameraDevice) {
            cameraDevice.rotation.y = -0.5 + Math.sin(Date.now() * 0.001) * 0.3;
        }
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}