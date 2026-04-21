import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export class CityVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`Container #${containerId} not found`);

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.devices = [];      // 存储三个设备对象
        this.vehicles = [];     // 存储小车对象
        this.timeOfDay = 12;
        this.cycleSpeed = 0.003;
        this.sunLight = null;
        this.ambientLight = null;
        this.stars = null;
        this.moon = null;

        this.init();
    }

    init() {
        // 场景
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a1030);
        this.scene.fog = new THREE.FogExp2(0x0a1030, 0.006);

        // 相机
        this.camera = new THREE.PerspectiveCamera(45, this.container.clientWidth / this.container.clientHeight, 0.1, 1000);
        this.camera.position.set(15, 12, 18);
        this.camera.lookAt(0, 0, 0);

        // 渲染器
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFShadowMap;
        this.container.appendChild(this.renderer.domElement);

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.target.set(0, 0, 0);

        // 光照
        this.setupLights();

        // 加载城市模型（异步，成功后添加设备和车辆）
        this.loadCityModel();

        // 启动动画循环
        this.animate();
    }

    setupLights() {
        this.ambientLight = new THREE.AmbientLight(0x404060, 0.6);
        this.scene.add(this.ambientLight);
        this.sunLight = new THREE.DirectionalLight(0xffffff, 1);
        this.sunLight.position.set(5, 10, 7);
        this.sunLight.castShadow = true;
        this.scene.add(this.sunLight);
        const backLight = new THREE.PointLight(0x4466ff, 0.4);
        backLight.position.set(-3, 5, -5);
        this.scene.add(backLight);
        const fillLight = new THREE.PointLight(0xccaa88, 0.5);
        fillLight.position.set(0, 10, 0);
        this.scene.add(fillLight);

        // 星星
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

        // 月亮
        const moonMat = new THREE.MeshStandardMaterial({ color: 0xdddddd, emissive: 0x444444 });
        this.moon = new THREE.Mesh(new THREE.SphereGeometry(0.8, 32, 32), moonMat);
        this.scene.add(this.moon);
    }

    loadCityModel() {
        const loader = new GLTFLoader();
        const modelPath = 'models/city/scene.gltf'; // 根据实际路径修改
        loader.load(modelPath,
            (gltf) => {
                const cityModel = gltf.scene;
                cityModel.position.set(0, -0.5, 0);
                cityModel.scale.set(30, 30, 30);
                cityModel.traverse(child => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });
                this.scene.add(cityModel);
                console.log('城市模型加载成功');
                this.addDevices();
                this.createTraffic();
            },
            (xhr) => {
                console.log(`城市模型加载中 ${Math.floor(xhr.loaded/xhr.total*100)}%`);
            },
            (error) => {
                console.error('城市模型加载失败', error);
            }
        );
    }

    addDevices() {
        const deviceConfigs = [
            { type: 'rsu', position: [13.01, 0.5, -9.00], scale: [0.5,0.5,0.5] },
            { type: 'camera', position: [-7.29, 0.5, -1.40], scale: [0.5,0.5,0.5] },
            { type: 'baseStation', position: [3.47, 0.5, 13.86], scale: [0.5,0.5,0.5] }
        ];

        deviceConfigs.forEach(cfg => {
            let group;
            if (cfg.type === 'baseStation') {
                group = new THREE.Group();
                group.userData = { id: 'baseStation' };
                const bodyMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.7, roughness: 0.4, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const body = new THREE.Mesh(new THREE.BoxGeometry(1.2, 2.2, 1.2), bodyMat);
                body.position.y = 1.1;
                group.add(body);
                const antennaMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 1.2), antennaMat);
                antenna.position.set(0, 2.3, 0);
                group.add(antenna);
                const topMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const topSphere = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8), topMat);
                topSphere.position.set(0, 2.9, 0);
                group.add(topSphere);
            } else if (cfg.type === 'camera') {
                group = new THREE.Group();
                group.userData = { id: 'camera' };
                const bodyMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.6, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const body = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.7, 1.4), bodyMat);
                body.position.y = 0.35;
                group.add(body);
                const lensMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const lens = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16), lensMat);
                lens.position.set(0, 0.35, 0.8);
                group.add(lens);
                const standMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const stand = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.6), standMat);
                stand.position.set(0, -0.2, 0);
                group.add(stand);
            } else if (cfg.type === 'rsu') {
                group = new THREE.Group();
                group.userData = { id: 'rsu' };
                const poleMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.25, 2.5), poleMat);
                pole.position.y = 1.25;
                group.add(pole);
                const armMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const arm = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.15, 0.3), armMat);
                arm.position.set(0, 2.6, 0);
                group.add(arm);
                const boxMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 });
                const box = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.5), boxMat);
                box.position.set(0, 2.9, 0);
                group.add(box);
            }
            if (group) {
                group.position.set(cfg.position[0], cfg.position[1], cfg.position[2]);
                group.scale.set(cfg.scale[0], cfg.scale[1], cfg.scale[2]);
                group.traverse(child => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });
                this.scene.add(group);
                this.devices.push(group);
            }
        });
    }

    createTraffic() {
        const routes = [
            {
                points: [
                    new THREE.Vector3(-14.18, 0.2, -13.23),
                    new THREE.Vector3(-15.13, 0.2, -0.31),
                    new THREE.Vector3(-9.27, 0.2, -0.14),
                    new THREE.Vector3(-9.96, 0.2, 6.62),
                    new THREE.Vector3(-15.77, 0.2, 6.35),
                    new THREE.Vector3(-16.16, 0.2, 10.72)
                ],
                color: 0xff3333,
                speed: 0.15
            },
            {
                points: [
                    new THREE.Vector3(6.49, 0.2, -18.25),
                    new THREE.Vector3(7.00, 0.2, -7.74),
                    new THREE.Vector3(1.24, 0.2, -6.20),
                    new THREE.Vector3(2.15, 0.2, -1.97),
                    new THREE.Vector3(19.11, 0.2, -3.37)
                ],
                color: 0x33ff33,
                speed: 0.15
            },
            {
                points: [
                    new THREE.Vector3(18.52, 0.2, 6.29),
                    new THREE.Vector3(2.20, 0.2, 7.32),
                    new THREE.Vector3(-1.79, 0.2, 7.43),
                    new THREE.Vector3(-3.38, 0.2, 9.24),
                    new THREE.Vector3(-3.59, 0.2, 14.60),
                    new THREE.Vector3(-13.52, 0.2, 14.16)
                ],
                color: 0x3399ff,
                speed: 0.15
            }
        ];

        const createCar = (color) => {
            const geometry = new THREE.BoxGeometry(0.8, 0.4, 1.2);
            const material = new THREE.MeshStandardMaterial({ color, metalness: 0.7, roughness: 0.3 });
            const car = new THREE.Mesh(geometry, material);
            car.castShadow = true;
            car.receiveShadow = true;
            return car;
        };

        routes.forEach(route => {
            const car = createCar(route.color);
            car.position.copy(route.points[0]);
            this.scene.add(car);
            this.vehicles.push({
                mesh: car,
                points: route.points,
                currentIdx: 0,
                direction: 1,
                speed: route.speed
            });
            // 可视化路径线（可选）
            const lineGeom = new THREE.BufferGeometry().setFromPoints(route.points);
            const lineMat = new THREE.LineBasicMaterial({ color: route.color });
            const pathLine = new THREE.Line(lineGeom, lineMat);
            this.scene.add(pathLine);
            route.points.forEach(p => {
                const marker = new THREE.Mesh(new THREE.SphereGeometry(0.15, 8, 8), new THREE.MeshStandardMaterial({ color: route.color }));
                marker.position.copy(p);
                this.scene.add(marker);
            });
        });
    }

    updateVehicles() {
        this.vehicles.forEach(vehicle => {
            const target = vehicle.points[vehicle.currentIdx];
            const pos = vehicle.mesh.position;
            const dist = pos.distanceTo(target);
            if (dist < 0.05) {
                vehicle.mesh.position.copy(target);
                let next = vehicle.currentIdx + vehicle.direction;
                if (next < 0 || next >= vehicle.points.length) {
                    vehicle.direction *= -1;
                    next = vehicle.currentIdx + vehicle.direction;
                }
                vehicle.currentIdx = next;
                return;
            }
            const dir = new THREE.Vector3().subVectors(target, pos).normalize();
            const step = dir.multiplyScalar(vehicle.speed);
            let newPos = pos.clone().add(step);
            if (newPos.distanceTo(target) > dist) newPos = target.clone();
            vehicle.mesh.position.copy(newPos);
            vehicle.mesh.rotation.y = Math.atan2(dir.x, dir.z);
        });
    }

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
        const nightFactor = 1 - intensityFactor;   // 添加这行

        this.sunLight.intensity = Math.min(1.5, intensityFactor * 1.5);
        this.ambientLight.intensity = 0.5 + intensityFactor * 0.7;

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

        if (intensityFactor < 0.3) {
            this.sunLight.color.setHex(0xffaa77);
        } else if (intensityFactor > 0.7) {
            this.sunLight.color.setHex(0xfff5e0);
        } else {
            this.sunLight.color.setHex(0xffddbb);
        }

        // 车辆自发光随夜晚变化（可选，如果不需要可注释）
        if (this.vehicles) {
            this.vehicles.forEach(vehicle => {
                vehicle.mesh.traverse(child => {
                    if (child.isMesh && child.material) {
                        const intensity = 0.3 + nightFactor * 0.7;
                        child.material.emissiveIntensity = intensity;
                    }
                });
            });
        }
    }

    changeNodeColor(nodeId, color, intensity = 0.8) {
        const device = this.devices.find(d => d.userData.id === nodeId);
        if (!device) return;
        const targetColor = (typeof color === 'number') ? new THREE.Color(color) : new THREE.Color(color);
        device.traverse(child => {
            if (child.isMesh && child.material) {
                const materials = Array.isArray(child.material) ? child.material : [child.material];
                materials.forEach(mat => {
                    mat.emissive = targetColor;
                    mat.emissiveIntensity = intensity;
                });
            }
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.updateDayNightCycle();
        this.updateVehicles();
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    resize(width, height) {
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
}