const ctx = document.getElementById('lidarChart').getContext('2d');
const data = {
    datasets: [{
        label: 'LIDAR',
        data: [],
        backgroundColor: 'rgba(0, 123, 255, 0.7)',
        pointRadius: 3,
        showLine: false
    }]
};

const config = {
    type: 'scatter',
    data: data,
    options: {
        responsive: true,
        scales: {
            x: {
                type: 'linear',
                min: -1500,
                max: 1500,
                title: { display: true, text: 'X (mm)' }
            },
            y: {
                type: 'linear',
                min: -1500,
                max: 1500,
                title: { display: true, text: 'Y (mm)' }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
};

const lidarChart = new Chart(ctx, config);

function polarToXY(angle, distance) {
    const radians = angle * Math.PI / 180;
    return {
        x: distance * Math.cos(radians),
        y: distance * Math.sin(radians)
    };
}

function updateChart() {
    fetch('/scan')
        .then(response => response.json())
        .then(scan => {
            data.datasets[0].data = scan.map(p => polarToXY(p.angle, p.distance));
            lidarChart.update();
        });
}

// Oppdater grafen hvert 500 ms
setInterval(updateChart, 500);
