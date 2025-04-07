const canvas = document.getElementById("lidar-canvas");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
    canvas.width = document.getElementById("lidar-container").clientWidth;
    canvas.height = document.getElementById("lidar-container").clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function drawScan(points) {
    // Rens skjermen
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const scale = Math.min(canvas.width, canvas.height) / 500; // 500cm = max 2.5m visning

    // Tegn sirkler (50, 100, 150, 200 cm)
    [50, 100, 150, 200].forEach(r => {
        ctx.beginPath();
        ctx.arc(centerX, centerY, r * scale, 0, 2 * Math.PI);
        ctx.strokeStyle = '#ccc';
        ctx.stroke();
    });

    // Tegn midten
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
    ctx.fillStyle = 'black';
    ctx.fill();

    // Tegn målepunkter
    points.forEach(p => {
        const angleRad = p.angle * (Math.PI / 180);
        const r = p.distance * scale;
        const x = centerX + r * Math.cos(angleRad);
        const y = centerY - r * Math.sin(angleRad);

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = "#007bff";
        ctx.fill();
    });
}

async function fetchScanData() {
    try {
        const res = await fetch("/scan");
        const data = await res.json();
        drawScan(data);
    } catch (e) {
        console.error("Klarte ikke hente LIDAR-data:", e);
    }
}

setInterval(fetchScanData, 300); // Hent data hvert 300ms
