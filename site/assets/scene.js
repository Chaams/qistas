// Qistas hero: a brass balance (al-qistas). The baseline sits on one pan, the pull request on the other.
// A failing PR is heavier with a red block and tips the beam; once fixed, the beam comes back level.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const stage = document.querySelector(".stage");
const canvas = document.getElementById("scene");
const cap = document.getElementById("stage-cap");
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
} catch {
  stage.classList.add("nogl");
}

if (renderer) {
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  camera.position.set(0, 2.0, 12);
  camera.lookAt(0, 1.25, 0);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x334, 0.7));
  const key = new THREE.DirectionalLight(0xfff1d6, 2.2);
  key.position.set(4, 8, 6);
  scene.add(key);

  const brass = new THREE.MeshStandardMaterial({ color: 0xc8963e, metalness: 0.9, roughness: 0.28 });
  const ink = new THREE.MeshStandardMaterial({ color: 0x18203a, metalness: 0.3, roughness: 0.55 });
  const pass = new THREE.MeshStandardMaterial({ color: 0x2f9e63, metalness: 0.2, roughness: 0.4 });
  const fail = new THREE.MeshStandardMaterial({ color: 0xd9463a, metalness: 0.2, roughness: 0.4, emissive: 0x4a0d08 });
  const neutral = new THREE.MeshStandardMaterial({ color: 0xe9e4d8, metalness: 0.1, roughness: 0.5 });

  const root = new THREE.Group();
  scene.add(root);

  // base + pillar
  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.25, 1.45, 0.22, 64), ink);
  base.position.y = -1.1;
  root.add(base);
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.8, 0.3, 48), brass);
  plinth.position.y = -0.85;
  root.add(plinth);
  const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 4.2, 24), brass);
  pillar.position.y = 1.2;
  root.add(pillar);
  const finial = new THREE.Mesh(new THREE.SphereGeometry(0.18, 32, 16), brass);
  finial.position.y = 3.55;
  root.add(finial);

  // beam (pivots at the top of the pillar)
  const PIVOT_Y = 3.25, HALF = 2.3;
  const beam = new THREE.Group();
  beam.position.y = PIVOT_Y;
  root.add(beam);
  const bar = new THREE.Mesh(new THREE.BoxGeometry(HALF * 2, 0.1, 0.12), brass);
  beam.add(bar);
  for (const s of [-1, 1]) {
    const tip = new THREE.Mesh(new THREE.SphereGeometry(0.09, 24, 12), brass);
    tip.position.x = s * HALF;
    beam.add(tip);
  }

  // pans: they hang from the beam ends and stay upright
  const CHAIN = 1.7;
  const bowl = new THREE.LatheGeometry(
    [new THREE.Vector2(0, -0.12), new THREE.Vector2(0.45, -0.1), new THREE.Vector2(0.78, 0.04), new THREE.Vector2(0.8, 0.06)], 64);
  function makePan() {
    const g = new THREE.Group();
    const pan = new THREE.Mesh(bowl, brass);
    pan.position.y = -CHAIN;
    g.add(pan);
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2;
      const end = new THREE.Vector3(Math.cos(a) * 0.72, -CHAIN + 0.05, Math.sin(a) * 0.72);
      const len = end.length();
      const c = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, len, 6), brass);
      c.position.copy(end).multiplyScalar(0.5);
      c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.clone().normalize());
      g.add(c);
    }
    root.add(g);
    return g;
  }
  const panL = makePan(), panR = makePan();

  // weights: test results stacked on each pan
  const cube = new THREE.BoxGeometry(0.32, 0.32, 0.32);
  function block(mat, x, y, z) {
    const m = new THREE.Mesh(cube, mat);
    m.position.set(x, -CHAIN + 0.2 + y, z);
    m.rotation.y = (x + z) * 2;
    return m;
  }
  [[-0.2, 0, 0], [0.2, 0, 0.05], [0, 0.32, 0]].forEach(([x, y, z]) => panL.add(block(pass, x, y, z)));
  [[-0.2, 0, 0], [0.2, 0, -0.05]].forEach(([x, y, z]) => panR.add(block(pass, x, y, z)));
  const bad = block(fail, 0, 0.32, 0);
  const good = block(pass, 0, 0.32, 0);
  panR.add(bad, good);

  // the five letters of al-qistas, orbiting
  const sprites = [];
  async function letters() {
    try { await document.fonts.load('600 96px "IBM Plex Sans Arabic"'); } catch {}
    [..."القسطاس"].forEach((ch, i, arr) => {
      const c = document.createElement("canvas");
      c.width = c.height = 128;
      const x = c.getContext("2d");
      x.font = '600 92px "IBM Plex Sans Arabic", "Noto Sans Arabic", Tahoma, sans-serif';
      x.textAlign = "center"; x.textBaseline = "middle";
      x.fillStyle = "#c8963e";
      x.fillText(ch, 64, 70);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, opacity: 0.55, depthWrite: false }));
      sp.scale.setScalar(0.62);
      sp.userData = { a: (i / arr.length) * Math.PI * 2, y: 0.6 + (i % 3) * 0.9 };
      root.add(sp);
      sprites.push(sp);
    });
    render(performance.now());
  }
  letters();

  // brass dust
  const N = 260, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const r = 3 + Math.random() * 3, a = Math.random() * Math.PI * 2;
    pos.set([Math.cos(a) * r, -1 + Math.random() * 6, Math.sin(a) * r - 1], i * 3);
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0xc8963e, size: 0.035, transparent: true, opacity: 0.6 }));
  scene.add(dust);

  // state: FAIL (PR heavier, tips right) <-> PASS (level)
  let failing = true, tilt = 0, swap = 0;
  const setCaption = () => {
    cap.innerHTML = failing
      ? '<b class="ko">PR #42 · FAIL</b> <span>dialect_match 0.77 &lt; 0.80</span>'
      : '<b class="ok">PR #43 · PASS</b> <span>dialect_match 0.95 ≥ 0.80</span>';
  };

  // pointer parallax
  let px = 0, py = 0;
  addEventListener("pointermove", (e) => {
    px = (e.clientX / innerWidth - 0.5) * 2;
    py = (e.clientY / innerHeight - 0.5) * 2;
  }, { passive: true });

  const tmp = new THREE.Vector3();
  let last = performance.now(), t0 = last;
  function render(now) {
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    const t = (now - t0) / 1000;

    if (!reduce && t - swap > 4.2) { failing = !failing; swap = t; setCaption(); }
    const target = failing ? -0.16 : 0;
    tilt += (target - tilt) * (1 - Math.exp(-dt * 3.2));
    beam.rotation.z = tilt + (reduce ? 0 : Math.sin(t * 1.3) * 0.006);

    const s = failing ? 1 : 0;
    bad.scale.setScalar(THREE.MathUtils.lerp(bad.scale.x, s + 0.001, 1 - Math.exp(-dt * 6)));
    good.scale.setScalar(THREE.MathUtils.lerp(good.scale.x, 1 - s + 0.001, 1 - Math.exp(-dt * 6)));

    for (const [pan, sx] of [[panL, -1], [panR, 1]]) {
      tmp.set(sx * HALF, 0, 0).applyEuler(beam.rotation).add(beam.position);
      pan.position.copy(tmp);
      pan.rotation.z = reduce ? 0 : Math.sin(t * 1.1 + sx) * 0.02;
    }

    root.rotation.y += ((reduce ? -0.35 : -0.35 + Math.sin(t * 0.25) * 0.25 + px * 0.35) - root.rotation.y) * 0.05;
    root.rotation.x += (py * 0.06 - root.rotation.x) * 0.05;
    dust.rotation.y = t * 0.03;
    sprites.forEach((sp) => {
      const a = sp.userData.a + t * 0.18;
      sp.position.set(Math.cos(a) * 3.4, sp.userData.y + Math.sin(t + sp.userData.a) * 0.12, Math.sin(a) * 1.6 - 0.6);
    });

    renderer.render(scene, camera);
  }

  function resize() {
    const { width, height } = canvas.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    render(performance.now());
  }
  new ResizeObserver(resize).observe(canvas);

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);
  if (reduce) {
    setCaption();
    tilt = -0.16;
    render(performance.now());
  } else {
    renderer.setAnimationLoop((now) => { if (visible) render(now); });
  }
}
