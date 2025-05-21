const THREE = require('three');
const { STLLoader } = require('three-stdlib');
const { OBJLoader } = require('three-stdlib');
const fs = require('fs');

function renderModel(modelPath, outputPath) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(200, 200);

  const ambientLight = new THREE.AmbientLight(0x404040);
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
  directionalLight.position.set(0, 1, 1);
  scene.add(ambientLight);
  scene.add(directionalLight);

  const extension = modelPath.split('.').pop().toLowerCase();
  let loader = extension === 'stl' ? new STLLoader() : new OBJLoader();

  loader.load(modelPath, (object) => {
    const geometry = extension === 'stl' ? object : object.children[0].geometry;
    const material = new THREE.MeshPhongMaterial({ color: 0x00ff00 });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    geometry.computeBoundingBox();
    const center = geometry.boundingBox.getCenter(new THREE.Vector3());
    mesh.position.sub(center);

    const size = geometry.boundingBox.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 5 / maxDim;
    mesh.scale.set(scale, scale, scale);

    camera.position.z = 10;
    renderer.render(scene, camera);

    const screenshot = renderer.domElement.toDataURL('image/png').split(',')[1];
    fs.writeFileSync(outputPath, Buffer.from(screenshot, 'base64'));
  });
}

if (process.argv.length === 4) {
  renderModel(process.argv[2], process.argv[3]);
}
