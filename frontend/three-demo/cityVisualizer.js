import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export class CityVisualizer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`Container #${containerId} not found`);

        this.options = { groundSize: 90, ...options };
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.buildings = [];
        this.devices = [];
        this.streetLamps = [];
        this.timeOfDay = 12;
        this.cycleSpeed = 0.003;
        this.sunLight = null;
        this.ambientLight = null;
        this.fillLight = null;
        this.stars = null;
        this.moon = null;
        this.textureLoader = new THREE.TextureLoader();

        // 车辆 & 红绿灯
        this.vehicles = [];
        this.trafficLights = [];
        this.trafficLightState = 'green';

        this.init();
    }

    init() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a1030);
        this.scene.fog = new THREE.FogExp2(0x0a1030, 0.006);

        this.camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
        this.camera.position.set(22, 14, 22);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFShadowMap;
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        this.controls.target.set(0, 3, 0);

        this.setupLights();
        this.createGround();
        this.createGrass();
        this.createBuildings();
        this.createRoads();
        this.createDevices();
        this.createStreetLamps();
        this.createStarsAndMoon();
        this.createTraffic();
        this.createTrafficLights();

        this.animate();
    }

    setupLights() {
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

        this.ambientLight = new THREE.AmbientLight(0x40460, 0.7);
        this.scene.add(this.ambientLight);

        this.fillLight = new THREE.PointLight(0xffaa66, 0.5);
        this.fillLight.position.set(-8, 8, -10);
        this.scene.add(this.fillLight);

        const fillLight2 = new THREE.PointLight(0xccaa88, 0.5);
        fillLight2.position.set(0, 10, 0);
        this.scene.add(fillLight2);
    }

    createGround() {
        const groundSize = this.options.groundSize;
        const groundGeometry = new THREE.PlaneGeometry(groundSize, groundSize);
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

    createGrass() {
        const groundSize = this.options.groundSize;
        const grassSize = groundSize - 2;
        const grassGeometry = new THREE.PlaneGeometry(grassSize, grassSize);

        const grassMaterial = new THREE.MeshStandardMaterial({
            color: 0x5c9e5c,
            roughness: 0.9,
            metalness: 0.1
        });

        this.textureLoader.load('textures/Grass005_1K-JPG_Color.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(4, 4);
                grassMaterial.map = texture;
            },
            undefined,
            (err) => console.warn('草地颜色贴图加载失败，使用纯色', err)
        );

        this.textureLoader.load('textures/Grass005_1K-JPG_NormalGL.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(4, 4);
                grassMaterial.normalMap = texture;
            },
            undefined,
            (err) => console.warn('草地法线贴图加载失败', err)
        );

        this.textureLoader.load('textures/Grass005_1K-JPG_Roughness.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(4, 4);
                grassMaterial.roughnessMap = texture;
            },
            undefined,
            (err) => console.warn('草地粗糙度贴图加载失败', err)
        );

        const grassPlane = new THREE.Mesh(grassGeometry, grassMaterial);
        grassPlane.rotation.x = -Math.PI / 2;
        grassPlane.position.y = -0.1;
        grassPlane.receiveShadow = true;
        this.scene.add(grassPlane);
    }

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

        let facadeColorMap = null;
        let facadeNormalMap = null;
        let facadeRoughnessMap = null;

        this.textureLoader.load('textures/Facade001_1K-JPG_Color.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                facadeColorMap = texture;
                this.buildings.forEach(building => {
                    if (building.material) {
                        building.material.map = facadeColorMap;
                        if (facadeNormalMap) building.material.normalMap = facadeNormalMap;
                        if (facadeRoughnessMap) building.material.roughnessMap = facadeRoughnessMap;
                    }
                });
            },
            undefined,
            (err) => console.warn('建筑颜色贴图加载失败，使用纯色', err)
        );

        this.textureLoader.load('textures/Facade001_1K-JPG_NormalGL.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                facadeNormalMap = texture;
                this.buildings.forEach(building => {
                    if (building.material) building.material.normalMap = facadeNormalMap;
                });
            },
            undefined,
            (err) => console.warn('建筑法线贴图加载失败', err)
        );

        this.textureLoader.load('textures/Facade001_1K-JPG_Roughness.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                facadeRoughnessMap = texture;
                this.buildings.forEach(building => {
                    if (building.material) building.material.roughnessMap = facadeRoughnessMap;
                });
            },
            undefined,
            (err) => console.warn('建筑粗糙度贴图加载失败', err)
        );

        blocks.forEach(block => {
            for (let k = 0; k < buildingsPerBlock; k++) {
                const offsetX = (Math.random() - 0.5) * (blockSize - buildingSpacing);
                const offsetZ = (Math.random() - 0.5) * (blockSize - buildingSpacing);
                let x = block.x + offsetX;
                let z = block.z + offsetZ;
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
                let repeatX = 1, repeatY = 1;
                if (facadeColorMap) {
                    repeatX = Math.max(1, Math.floor(width * 1.5));
                    repeatY = Math.max(2, Math.floor(height * 2.0));
                    facadeColorMap.repeat.set(repeatX, repeatY);
                    if (facadeNormalMap) facadeNormalMap.repeat.set(repeatX, repeatY);
                    if (facadeRoughnessMap) facadeRoughnessMap.repeat.set(repeatX, repeatY);
                }
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

    createRoads() {
        const blockSize = 14;
        const blocks = [];
        for (let i = -3; i <= 3; i++) {
            for (let j = -3; j <= 3; j++) {
                if (Math.abs(i) <= 1 && Math.abs(j) <= 1) continue;
                blocks.push({ x: i * blockSize, z: j * blockSize });
            }
        }

        let roadColorMap = null;
        let roadNormalMap = null;
        let roadRoughnessMap = null;

        this.textureLoader.load('textures/Road008B_1K-JPG_Color.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(2, 2);
                roadColorMap = texture;
            },
            undefined,
            (err) => console.warn('道路颜色贴图加载失败，使用纯色', err)
        );

        this.textureLoader.load('textures/Road008B_1K-JPG_NormalGL.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(2, 2);
                roadNormalMap = texture;
            },
            undefined,
            (err) => console.warn('道路法线贴图加载失败', err)
        );

        this.textureLoader.load('textures/Road008B_1K-JPG_Roughness.jpg',
            (texture) => {
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.repeat.set(2, 2);
                roadRoughnessMap = texture;
            },
            undefined,
            (err) => console.warn('道路粗糙度贴图加载失败', err)
        );

        const roadMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a3a3a,
            roughness: 0.8,
            metalness: 0.1
        });

        const update = () => {
            if (roadColorMap) roadMaterial.map = roadColorMap;
            if (roadNormalMap) roadMaterial.normalMap = roadNormalMap;
            if (roadRoughnessMap) roadMaterial.roughnessMap = roadRoughnessMap;
            roadMaterial.needsUpdate = true;
        };

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

    createCarModel(color) {
        const group = new THREE.Group();
        const bodyGeo = new THREE.BoxGeometry(0.9, 0.4, 1.4);
        const bodyMat = new THREE.MeshStandardMaterial({
            color: color,
            metalness: 0.7,
            roughness: 0.3,
            emissive: 0x442200,
            emissiveIntensity: 0.5
        });
        const body = new THREE.Mesh(bodyGeo, bodyMat);
        body.position.y = 0.2;
        group.add(body);
        const roofGeo = new THREE.BoxGeometry(0.7, 0.2, 1.0);
        const roofMat = new THREE.MeshStandardMaterial({
            color: 0x88aaff,
            metalness: 0.9,
            emissive: 0x442200,
            emissiveIntensity: 0.5
        });
        const roof = new THREE.Mesh(roofGeo, roofMat);
        roof.position.y = 0.45;
        group.add(roof);
        const wheelMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.2 });
        const wheelGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16);
        const wheelPositions = [
            [-0.5, 0.1, -0.7], [0.5, 0.1, -0.7],
            [-0.5, 0.1, 0.7], [0.5, 0.1, 0.7]
        ];
        wheelPositions.forEach(pos => {
            const wheel = new THREE.Mesh(wheelGeo, wheelMat);
            wheel.rotation.z = Math.PI / 2;
            wheel.position.set(pos[0], pos[1], pos[2]);
            group.add(wheel);
        });
        return group;
    }

    createTraffic() {
        console.log('createTraffic 执行');
        const blockSize = 14;
        const blocks = [];
        for (let i = -3; i <= 3; i++) {
            for (let j = -3; j <= 3; j++) {
                if (Math.abs(i) <= 1 && Math.abs(j) <= 1) continue;
                blocks.push({ x: i * blockSize, z: j * blockSize });
            }
        }
        const uniqueX = [...new Set(blocks.map(b => b.x))];
        const uniqueZ = [...new Set(blocks.map(b => b.z))];

        this.vehicles = [];

        uniqueX.forEach(x => {
            const zMin = Math.min(...blocks.filter(b => b.x === x).map(b => b.z));
            const zMax = Math.max(...blocks.filter(b => b.x === x).map(b => b.z));
            const startZ = zMin - blockSize/2;
            const endZ = zMax + blockSize/2;
            const car = this.createCarModel(0xff5533);
            car.castShadow = true;
            car.receiveShadow = true;
            car.position.set(x, 0.1, startZ);
            this.scene.add(car);
            this.vehicles.push({
                mesh: car,
                axis: 'z',
                start: startZ,
                end: endZ,
                direction: 1,
                speed: 0.05,
                pos: startZ
            });
        });

        uniqueZ.forEach(z => {
            const xMin = Math.min(...blocks.filter(b => b.z === z).map(b => b.x));
            const xMax = Math.max(...blocks.filter(b => b.z === z).map(b => b.x));
            const startX = xMin - blockSize/2;
            const endX = xMax + blockSize/2;
            const car = this.createCarModel(0x33aaff);
            car.castShadow = true;
            car.receiveShadow = true;
            car.position.set(startX, 0.1, z);
            this.scene.add(car);
            this.vehicles.push({
                mesh: car,
                axis: 'x',
                start: startX,
                end: endX,
                direction: 1,
                speed: 0.05,
                pos: startX
            });
        });
        console.log('车辆数量:', this.vehicles.length);
    }

    createTrafficLights() {
        const poleMat = new THREE.MeshStandardMaterial({ color: 0x666666 });
        this.trafficLights = [];

        const positions = [[-4, 0, -4], [4, 0, -4], [-4, 0, 4], [4, 0, 4]];
        positions.forEach(pos => {
            const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.4, 3), poleMat);
            pole.position.set(pos[0], 1.5, pos[2]);
            this.scene.add(pole);

            const box = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.6), new THREE.MeshStandardMaterial({ color: 0x333333 }));
            box.position.set(pos[0], 2.8, pos[2]);
            this.scene.add(box);

            const redMat = new THREE.MeshStandardMaterial({ color: 0xff0000, emissive: 0xff0000, emissiveIntensity: 0.5 });
            const redLight = new THREE.Mesh(new THREE.SphereGeometry(0.2), redMat);
            redLight.position.set(pos[0], 2.9, pos[2] + 0.2);
            this.scene.add(redLight);

            const greenMat = new THREE.MeshStandardMaterial({ color: 0x00ff00, emissive: 0x00ff00, emissiveIntensity: 0.5 });
            const greenLight = new THREE.Mesh(new THREE.SphereGeometry(0.2), greenMat);
            greenLight.position.set(pos[0], 2.5, pos[2] + 0.2);
            this.scene.add(greenLight);

            this.trafficLights.push({
                red: redMat,
                green: greenMat,
                redMesh: redLight,
                greenMesh: greenLight
            });
        });
    }

    createDevices() {
        const baseStation = new THREE.Group();
        baseStation.userData = { id: 'baseStation' };
        const bodyMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            metalness: 0.7,
            roughness: 0.4,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const body = new THREE.Mesh(new THREE.BoxGeometry(1.2, 2.2, 1.2), bodyMat);
        body.position.y = 1.1;
        body.castShadow = true;
        baseStation.add(body);
        const antennaMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 1.2), antennaMat);
        antenna.position.set(0, 2.3, 0);
        antenna.castShadow = true;
        baseStation.add(antenna);
        const topMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const topSphere = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8), topMat);
        topSphere.position.set(0, 2.9, 0);
        baseStation.add(topSphere);
        baseStation.position.set(-11, 0, -9);
        baseStation.castShadow = true;
        this.scene.add(baseStation);
        this.devices.push(baseStation);

        const cameraGroup = new THREE.Group();
        cameraGroup.userData = { id: 'camera' };
        const camBodyMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            metalness: 0.6,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const camBody = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.7, 1.4), camBodyMat);
        camBody.position.y = 0.35;
        camBody.castShadow = true;
        cameraGroup.add(camBody);
        const lensMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const lens = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16), lensMat);
        lens.position.set(0, 0.35, 0.8);
        lens.castShadow = true;
        cameraGroup.add(lens);
        const standMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const stand = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.6), standMat);
        stand.position.set(0, -0.2, 0);
        stand.castShadow = true;
        cameraGroup.add(stand);
        cameraGroup.position.set(9, 0.7, 7);
        cameraGroup.rotation.y = -0.5;
        this.scene.add(cameraGroup);
        this.devices.push(cameraGroup);

        const rsuGroup = new THREE.Group();
        rsuGroup.userData = { id: 'rsu' };
        const poleMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.25, 2.5), poleMat);
        pole.position.y = 1.25;
        pole.castShadow = true;
        rsuGroup.add(pole);
        const armMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const arm = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.15, 0.3), armMat);
        arm.position.set(0, 2.6, 0);
        arm.castShadow = true;
        rsuGroup.add(arm);
        const boxMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffff,
            emissiveIntensity: 0.8
        });
        const box = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.5), boxMat);
        box.position.set(0, 2.9, 0);
        box.castShadow = true;
        rsuGroup.add(box);
        rsuGroup.position.set(4, 0, -10);
        this.scene.add(rsuGroup);
        this.devices.push(rsuGroup);
    }

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
        this.ambientLight.intensity = 0.5 + intensityFactor * 0.7;
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
        this.buildings.forEach(building => {
            if (building.material) {
                building.material.emissiveIntensity = 0.15 + nightFactor * 0.4;
            }
        });

        if (intensityFactor < 0.3) {
            this.sunLight.color.setHex(0xffaa77);
        } else if (intensityFactor > 0.7) {
            this.sunLight.color.setHex(0xfff5e0);
        } else {
            this.sunLight.color.setHex(0xffddbb);
        }

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

    highlightNode(nodeId, intensity = 1, color = 0xffaa00) {
        const device = this.devices.find(d => d.userData.id === nodeId);
        if (!device) {
            console.warn(`Device ${nodeId} not found`);
            return;
        }

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

    setView(viewName) {
        switch(viewName) {
            case 'global':
                this.camera.position.set(16, 14, 22);
                this.controls.target.set(0, 3, 0);
                break;
            case 'congested':
                this.camera.position.set(-7, 6, 6);
                this.controls.target.set(-11, 0, -9);
                break;
            case 'bestNode':
                this.camera.position.set(-1, 3, 12);
                this.controls.target.set(9, 0.7, 7);
                break;
            default:
                console.warn('未知视角:', viewName);
                return;
        }
        this.controls.update();
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.updateDayNightCycle();

        const isGreen = (Math.floor(Date.now() / 5000) % 2 === 0);
        this.trafficLightState = isGreen ? 'green' : 'red';

        if (this.trafficLights) {
            this.trafficLights.forEach(light => {
                if (isGreen) {
                    light.red.emissiveIntensity = 0.1;
                    light.green.emissiveIntensity = 0.8;
                } else {
                    light.red.emissiveIntensity = 0.8;
                    light.green.emissiveIntensity = 0.1;
                }
            });
        }

        if (this.vehicles && this.vehicles.length) {
            const intersectionX = 0, intersectionZ = 0;
            const stopDist = 2.5;
            this.vehicles.forEach(vehicle => {
                let speed = vehicle.speed;
                const posX = vehicle.mesh.position.x;
                const posZ = vehicle.mesh.position.z;

                let nearIntersection = false;
                if (vehicle.axis === 'x') {
                    const distToIntersection = Math.abs(posX - intersectionX);
                    nearIntersection = (distToIntersection < stopDist);
                    if ((vehicle.direction === 1 && posX > 0) || (vehicle.direction === -1 && posX < 0)) {
                        nearIntersection = false;
                    }
                } else {
                    const distToIntersection = Math.abs(posZ - intersectionZ);
                    nearIntersection = (distToIntersection < stopDist);
                    if ((vehicle.direction === 1 && posZ > 0) || (vehicle.direction === -1 && posZ < 0)) {
                        nearIntersection = false;
                    }
                }

                if (nearIntersection && this.trafficLightState === 'red') {
                    speed = 0;
                }

                vehicle.pos += speed * vehicle.direction;

                if (vehicle.pos >= vehicle.end) {
                    vehicle.pos = vehicle.end;
                    vehicle.direction = -1;
                } else if (vehicle.pos <= vehicle.start) {
                    vehicle.pos = vehicle.start;
                    vehicle.direction = 1;
                }

                if (vehicle.axis === 'x') {
                    vehicle.mesh.position.x = vehicle.pos;
                } else {
                    vehicle.mesh.position.z = vehicle.pos;
                }

                const angle = (vehicle.direction === 1) ? 0 : Math.PI;
                vehicle.mesh.rotation.y = angle;
            });
        }

        const cameraDevice = this.devices.find(d => d.userData.id === 'camera');
        if (cameraDevice) {
            cameraDevice.rotation.y = -0.5 + Math.sin(Date.now() * 0.001) * 0.3;
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    // 占位空函数，避免报错
    loadCityModel() {}
    updateVehicles() {}
}