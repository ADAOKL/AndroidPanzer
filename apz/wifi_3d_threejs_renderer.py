"""WIFI 3D THREEJS RENDERER: Professionelle 3D-Visualisierung mit Three.js!

Erzeugt vollständige 3D-HTML-Dateien mit:
  • Interactive 3D-Szene
  • Raum-Koordinaten System
  • Grid-Floor (Gitterfloor)
  • Raum-Boxen (wireframe)
  • Access Points als Kugeln
  • Person als Würfel/Marker
  • Kamera-Kontrollen
  • Beleuchtung & Shading
"""
from __future__ import annotations

from typing import List, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class AccessPoint3D:
    """3D Access Point."""
    name: str
    x: float
    y: float
    z: float
    signal_strength: int
    color: str = "#00FF00"  # Grün


@dataclass
class Position3D:
    """3D Position."""
    x: float
    y: float
    z: float


class ThreeJSRenderer:
    """Three.js 3D Renderer für WiFi Room Scanner."""

    def __init__(self, width: float = 6.5, height: float = 3.0, depth: float = 8.2):
        """Initialisiere Renderer."""
        self.width = width
        self.height = height
        self.depth = depth
        self.access_points: List[AccessPoint3D] = []
        self.person_position: Optional[Position3D] = None
        self.trajectory: List[Position3D] = []

    def add_access_point(self, name: str, x: float, y: float, z: float, signal: int) -> None:
        """Füge Access Point hinzu."""
        # Farbcodierung basierend auf Signal
        if signal > -50:
            color = "#00FF00"  # Grün - Ausgezeichnet
        elif signal > -60:
            color = "#FFFF00"  # Gelb - Sehr Gut
        elif signal > -75:
            color = "#FFA500"  # Orange - Moderat
        else:
            color = "#FF0000"  # Rot - Schwach

        self.access_points.append(AccessPoint3D(name, x, y, z, signal, color))

    def set_person_position(self, x: float, y: float, z: float) -> None:
        """Setze Person Position."""
        self.person_position = Position3D(x, y, z)

    def add_trajectory_point(self, x: float, y: float, z: float) -> None:
        """Füge Trajektorie-Punkt hinzu."""
        self.trajectory.append(Position3D(x, y, z))

    def generate_html(self, filename: str = "wifi_3d_scan.html") -> str:
        """Generiere vollständige HTML-Datei mit Three.js."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi 3D Room Scanner - Interactive Visualization</title>
    <style>
        body {{
            margin: 0;
            overflow: hidden;
            background: #001a4d;
            font-family: 'Arial', sans-serif;
        }}
        #canvas {{
            display: block;
            width: 100%;
            height: 100vh;
        }}
        #info {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: #0f0;
            padding: 15px;
            border: 2px solid #0f0;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-width: 350px;
            z-index: 100;
        }}
        #controls {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: #0f0;
            padding: 15px;
            border: 2px solid #0f0;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 100;
        }}
        .label {{
            color: #00ff00;
            font-weight: bold;
        }}
        .value {{
            color: #ffff00;
        }}
        button {{
            background: #001a4d;
            color: #0f0;
            border: 1px solid #0f0;
            padding: 5px 10px;
            margin: 5px 0;
            cursor: pointer;
            border-radius: 3px;
        }}
        button:hover {{
            background: #003366;
        }}
    </style>
</head>
<body>
    <div id="info">
        <div class="label">WiFi 3D ROOM SCANNER</div>
        <div style="margin-top: 5px;">
            <div><span class="label">Raum:</span> <span class="value">{self.width:.1f}m × {self.depth:.1f}m × {self.height:.1f}m</span></div>
            <div><span class="label">Volumen:</span> <span class="value">{self.width * self.depth * self.height:.1f}m³</span></div>
            <div style="margin-top: 10px;">
                <div class="label">Access Points: {len(self.access_points)}</div>
"""

        for ap in self.access_points:
            html += f"""                <div style="margin: 5px 0;">
                    ● {ap.name} ({ap.x:.1f}, {ap.y:.1f}, {ap.z:.1f}) - {ap.signal_strength}dBm
                </div>
"""

        html += """            </div>
        </div>
    </div>

    <div id="controls">
        <div class="label">CONTROLS</div>
        <div style="margin: 5px 0;">
            <button onclick="resetCamera()">Reset View</button>
            <button onclick="toggleGrid()">Toggle Grid</button>
            <button onclick="toggleWireframe()">Wireframe</button>
        </div>
        <div style="margin-top: 10px; font-size: 11px;">
            <div>Mouse: Drag to rotate</div>
            <div>Scroll: Zoom in/out</div>
            <div>Right Click: Pan</div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@r128/examples/js/controls/OrbitControls.js"></script>

    <script>
        let scene, camera, renderer, controls, gridHelper, wireframeMode = false;

        function init() {
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x001a4d);
            scene.fog = new THREE.Fog(0x001a4d, 100, 200);

            // Camera
            camera = new THREE.PerspectiveCamera(
                75,
                window.innerWidth / window.innerHeight,
                0.1,
                1000
            );
            camera.position.set({self.width/2}, {self.height + 3}, {self.depth + 3});
            camera.lookAt({self.width/2}, {self.height/2}, {self.depth/2});

            // Renderer
            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFShadowShadowMap;
            document.body.appendChild(renderer.domElement);

            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.target.set({self.width/2}, {self.height/2}, {self.depth/2});
            controls.autoRotate = true;
            controls.autoRotateSpeed = 2;
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.update();

            // Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set({self.width}, {self.height * 2}, {self.depth});
            directionalLight.castShadow = true;
            directionalLight.shadow.mapSize.width = 2048;
            directionalLight.shadow.mapSize.height = 2048;
            scene.add(directionalLight);

            // Grid Floor
            createGridFloor();

            // Room Box (Wireframe)
            createRoomBox();

            // Coordinate System
            createCoordinateSystem();

            // Access Points
            createAccessPoints();

            // Person Position
            if ({json.dumps(self.person_position is not None)}) {{
                createPersonMarker();
            }}

            // Trajectory
            if ({len(self.trajectory)} > 0) {{
                createTrajectory();
            }}

            // Window resize
            window.addEventListener('resize', onWindowResize);

            // Animation loop
            animate();
        }

        function createGridFloor() {{
            gridHelper = new THREE.GridHelper({self.width}, 20, 0x004d4d, 0x003333);
            gridHelper.position.y = 0;
            scene.add(gridHelper);

            // Floor geometry
            const floorGeometry = new THREE.PlaneGeometry({self.width}, {self.depth});
            const floorMaterial = new THREE.MeshStandardMaterial({{
                color: 0x001a33,
                roughness: 0.8,
                metalness: 0.2
            }});
            const floor = new THREE.Mesh(floorGeometry, floorMaterial);
            floor.rotation.x = -Math.PI / 2;
            floor.position.y = 0;
            floor.receiveShadow = true;
            scene.add(floor);
        }}

        function createRoomBox() {{
            const geometry = new THREE.BoxGeometry({self.width}, {self.height}, {self.depth});
            const edges = new THREE.EdgesGeometry(geometry);
            const lineSegments = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0xffffff, linewidth: 2 }}));
            lineSegments.position.set({self.width/2}, {self.height/2}, {self.depth/2});
            scene.add(lineSegments);

            // Room label
            const canvas = document.createElement('canvas');
            canvas.width = 512;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#00ff00';
            ctx.font = 'Bold 40px Arial';
            ctx.fillText('ROOM: {self.width:.1f}m x {self.depth:.1f}m x {self.height:.1f}m', 10, 50);
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMaterial = new THREE.SpriteMaterial({{ map: texture }});
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.position.set({self.width/2}, {self.height + 1}, 0);
            sprite.scale.set(8, 2, 1);
            scene.add(sprite);
        }}

        function createCoordinateSystem() {{
            const axesHelper = new THREE.AxesHelper(5);
            scene.add(axesHelper);

            // X axis (red)
            const xGeometry = new THREE.BufferGeometry();
            xGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array([0, 0, 0, 5, 0, 0]), 3));
            const xMaterial = new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }});
            const xLine = new THREE.Line(xGeometry, xMaterial);
            scene.add(xLine);

            // Y axis (green)
            const yGeometry = new THREE.BufferGeometry();
            yGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array([0, 0, 0, 0, 5, 0]), 3));
            const yMaterial = new THREE.LineBasicMaterial({{ color: 0x00ff00, linewidth: 3 }});
            const yLine = new THREE.Line(yGeometry, yMaterial);
            scene.add(yLine);

            // Z axis (blue)
            const zGeometry = new THREE.BufferGeometry();
            zGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array([0, 0, 0, 0, 0, 5]), 3));
            const zMaterial = new THREE.LineBasicMaterial({{ color: 0x0000ff, linewidth: 3 }});
            const zLine = new THREE.Line(zGeometry, zMaterial);
            scene.add(zLine);
        }}

        function createAccessPoints() {{
"""

        # Füge Access Points hinzu
        for i, ap in enumerate(self.access_points):
            html += f"""            // {ap.name}
            {{
                const geometry = new THREE.SphereGeometry(0.15, 32, 32);
                const material = new THREE.MeshStandardMaterial({{
                    color: '{ap.color}',
                    emissive: '{ap.color}',
                    metalness: 0.8,
                    roughness: 0.2
                }});
                const sphere = new THREE.Mesh(geometry, material);
                sphere.position.set({ap.x}, {ap.z}, {ap.y});
                sphere.castShadow = true;
                sphere.receiveShadow = true;
                scene.add(sphere);

                // Label
                const canvas = document.createElement('canvas');
                canvas.width = 256;
                canvas.height = 64;
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '{ap.color}';
                ctx.font = 'Bold 20px Arial';
                ctx.fillText('{ap.name}', 10, 30);
                ctx.fillText('{ap.signal_strength}dBm', 10, 50);
                const texture = new THREE.CanvasTexture(canvas);
                const spriteMaterial = new THREE.SpriteMaterial({{ map: texture }});
                const sprite = new THREE.Sprite(spriteMaterial);
                sprite.position.copy(sphere.position);
                sprite.position.y += 0.5;
                sprite.scale.set(2, 0.5, 1);
                scene.add(sprite);
            }}
"""

        html += """        }

        function createPersonMarker() {
"""

        if self.person_position:
            html += f"""            const geometry = new THREE.BoxGeometry(0.2, 0.4, 0.2);
            const material = new THREE.MeshStandardMaterial({{
                color: 0x0088ff,
                emissive: 0x0088ff,
                metalness: 0.6,
                roughness: 0.4
            }});
            const cube = new THREE.Mesh(geometry, material);
            cube.position.set({self.person_position.x}, {self.person_position.z}, {self.person_position.y});
            cube.castShadow = true;
            cube.receiveShadow = true;
            scene.add(cube);

            // Label
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 64;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#0088ff';
            ctx.font = 'Bold 20px Arial';
            ctx.fillText('PERSON', 10, 30);
            ctx.fillText('({self.person_position.x:.1f}, {self.person_position.y:.1f}, {self.person_position.z:.1f})', 10, 50);
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMaterial = new THREE.SpriteMaterial({{ map: texture }});
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.position.copy(cube.position);
            sprite.position.y += 0.5;
            sprite.scale.set(2.5, 0.6, 1);
            scene.add(sprite);
"""

        html += """        }

        function createTrajectory() {
            const points = [
"""

        for pt in self.trajectory:
            html += f"                new THREE.Vector3({pt.x}, {pt.z}, {pt.y}),\n"

        html += """            ];

            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const material = new THREE.LineBasicMaterial({{ color: 0xffaa00, linewidth: 2 }});
            const line = new THREE.Line(geometry, material);
            scene.add(line);

            // Trajectory points
            const pointGeometry = new THREE.SphereGeometry(0.05, 16, 16);
            const pointMaterial = new THREE.MeshStandardMaterial({{ color: 0xffaa00 }});
            points.forEach((point, index) => {
                const sphere = new THREE.Mesh(pointGeometry, pointMaterial);
                sphere.position.copy(point);
                scene.add(sphere);
            });
        }

        function toggleGrid() {
            gridHelper.visible = !gridHelper.visible;
        }

        function toggleWireframe() {
            scene.traverse((child) => {
                if (child.isMesh) {
                    child.material.wireframe = !child.material.wireframe;
                }
            });
            wireframeMode = !wireframeMode;
        }

        function resetCamera() {
            camera.position.set(""" + f"""{self.width/2}""" + """, """ + f"""{self.height + 3}""" + """, """ + f"""{self.depth + 3}""" + """);
            camera.lookAt(""" + f"""{self.width/2}""" + """, """ + f"""{self.height/2}""" + """, """ + f"""{self.depth/2}""" + """);
            controls.target.set(""" + f"""{self.width/2}""" + """, """ + f"""{self.height/2}""" + """, """ + f"""{self.depth/2}""" + """);
            controls.update();
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        init();
    </script>
</body>
</html>
"""
        return html

    def save_html(self, filename: str = "wifi_3d_scan.html") -> str:
        """Speichere HTML-Datei."""
        html = self.generate_html(filename)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        return filename


def create_threejs_renderer(width: float = 6.5, height: float = 3.0, depth: float = 8.2) -> ThreeJSRenderer:
    """Factory: Erstellt Three.js Renderer."""
    return ThreeJSRenderer(width, height, depth)
