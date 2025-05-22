let workbookData = [];

window.addEventListener('DOMContentLoaded', loadExcelData);

function loadExcelData() {
    fetch('../static/media/TestUnix.xlsx')
        .then(response => response.arrayBuffer())
        .then(arrayBuffer => {
            const data = new Uint8Array(arrayBuffer);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheetName = workbook.SheetNames[0];
            const sheet = workbook.Sheets[firstSheetName];
            workbookData = XLSX.utils.sheet_to_json(sheet, { defval: "" });
            console.log("✅ Dữ liệu đã được load!");
            console.log(workbookData);

            // Vẽ biểu đồ sau khi load xong
            drawChart1();
            drawChart2();
            drawChart3();
            drawChart4();
        })
        .catch(error => {
            console.error("❌ Lỗi khi tải file Excel:", error);
        });
}

function filterData() {
    return workbookData.filter(d => d["Phương Thức Xét Tuyển"] === "thpt quốc gia");
}

// ------------------ Chart 1 ------------------
function drawChart1() {
    fetch('/api/chart1')
        .then(response => response.json())
        .then(data => {
            const schools = [...new Set(data.map(item => item['Tên trường']))];

            const traces = schools.map(school => {
                const filtered = data.filter(item => item['Tên trường'] === school);
                return {
                    x: filtered.map(item => item['Năm']),
                    y: filtered.map(item => item['Điểm Chuẩn']),
                    name: school,
                    type: 'bar'
                };
            });

            const layout = {
                title: 'Chart 1: Điểm và Năm theo Ngành và Trường',
                barmode: 'group',
                xaxis: { title: 'Năm' },
                yaxis: { title: 'Điểm Chuẩn' }
            };

            Plotly.newPlot('bar-chart1', traces, layout);
        })
        .catch(error => console.error('❌ Lỗi khi vẽ Chart 1:', error));
}

// ------------------ Chart 2 ------------------
function drawChart2() {
    fetch('/api/chart2')
        .then(response => response.json())
        .then(data => {
            const years = [...new Set(data.map(item => item['Năm']))];

            const traces = years.map(year => {
                const filtered = data.filter(item => item['Năm'] === year);
                return {
                    x: filtered.map(item => item['Tên trường']),
                    y: filtered.map(item => item['Điểm Chuẩn']),
                    name: year.toString(),
                    type: 'bar'
                };
            });

            const layout = {
                title: 'Chart 2: Trường và Điểm theo Năm và Ngành',
                barmode: 'group',
                xaxis: { title: 'Tên trường' },
                yaxis: { title: 'Điểm Chuẩn' }
            };

            Plotly.newPlot('bar-chart2', traces, layout);
        })
        .catch(error => console.error('❌ Lỗi khi vẽ Chart 2:', error));
}

// ------------------ Chart 3 ------------------
function drawChart3() {
    fetch('/api/chart3')
        .then(response => response.json())
        .then(data => {
            const barTraces = data.map((item, index) => ({
                x: [item['Năm']],
                y: [item['Điểm Chuẩn']],
                name: `Năm ${item['Năm']}`,
                type: 'bar',
                marker: {
                    color: `hsl(${index * 45}, 70%, 50%)`
                },
                yaxis: 'y1'
            }));

            const lineTrace = {
                x: data.map(item => item['Năm']),
                y: data.map(item => item['Số lượng ngành']),
                name: 'Số lượng ngành',
                type: 'scatter',
                mode: 'lines+markers',
                yaxis: 'y2',
                line: { color: 'orange' }
            };

            const layout = {
                title: 'So sánh Điểm Chuẩn và Số lượng Ngành theo Năm',
                xaxis: { title: 'Năm' },
                yaxis: { title: 'Điểm Chuẩn TB' },
                yaxis2: {
                    title: 'Số lượng ngành',
                    overlaying: 'y',
                    side: 'right'
                },
                legend: { x: 0, y: 1.2 }
            };

            Plotly.newPlot('bar-chart3', [...barTraces, lineTrace], layout);
        })
        .catch(error => console.error('❌ Lỗi khi vẽ Chart 3:', error));
}

// ------------------ Chart 4 ------------------
function drawChart4() {
    fetch('/api/chart4')
        .then(response => response.json())
        .then(data => {
            const schools = [...new Set(data.map(item => item['Tên trường']))];

            const traces = schools.map(school => {
                const filtered = data.filter(item => item['Tên trường'] === school);
                return {
                    x: filtered.map(item => item['Năm']),
                    y: filtered.map(item => item['Điểm Chuẩn']),
                    name: school,
                    type: 'scatter'
                };
            });

            const layout = {
                title: 'Chart 4: Năm và Điểm theo Trường',
                xaxis: { title: 'Năm' },
                yaxis: { title: 'Điểm Chuẩn' }
            };

            Plotly.newPlot('bar-chart4', traces, layout);
        })
        .catch(error => console.error('❌ Lỗi khi vẽ Chart 4:', error));
}
