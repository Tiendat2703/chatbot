
$(document).ready(function () {
    applyFilters();

    $('#filter-btn').on('click', function () {
        setTimeout(() => {
            document.getElementById("chart1").scrollIntoView({ behavior: 'smooth' });
        }, 300);
    });

    $('#school').on('change', function () {
        const selectedSchools = $('#school').val();
        $.ajax({
            url: '/majors-by-schools',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ schools: selectedSchools }),
            success: function (res) {
                const majorSelect = $('#major');
                majorSelect.empty();
                majorSelect.append(`<option value="__all__">Tất cả các ngành</option>`);
                res.majors.forEach(m => {
                    majorSelect.append(`<option value="${m}">${m}</option>`);
                });
                majorSelect.trigger('change');
            }
        });
    });

    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function () {
        ['chart1', 'chart2', 'chart3', 'chart4'].forEach(id => {
            if (document.getElementById(id)) {
                Plotly.Plots.resize(document.getElementById(id));
            }
        });
    });

    $('#suggest-btn').on('click', function () {
        const min = parseFloat($('#score-min').val()) || 0;
        const max = parseFloat($('#score-max').val()) || 100;
        const year = $('#suggest-year').val();
        const method = $('#suggest-method').val();

        $.ajax({
            url: '/suggest',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                year: year,
                method: method,
                minScore: min,
                maxScore: max
            }),
            success: function (data) {
                const table = $('#suggestion-table tbody');
                table.empty();
                if (data.length === 0) {
                    table.append('<tr><td colspan="5" class="text-center text-muted">Không có kết quả phù hợp.</td></tr>');
                    return;
                }
                $('#suggestion-table').show();
                data.forEach(item => {
                    table.append(`<tr>
                        <td>${item.school}</td>
                        <td>${item.major}</td>
                        <td>${item.method}</td>
                        <td>${item.score}</td>
                        <td>${item.year}</td>
                    </tr>`);
                });
            },
            error: function (err) {
                alert("❌ Đã xảy ra lỗi khi gợi ý.");
                console.error(err);
            }
        });
    });
});

let chartData = {};

function applyFilters() {
    const year = $('#year').val() || [];
    const school = $('#school').val() || [];
    const major = $('#major').val() || [];
    let method = $('#method').val() || [];
    if (method.includes('__all__')) {
        method = ['__all__'];
    }


    $('#loading').show();
    $('#chart1, #chart2, #chart3, #chart4').html('');
    $('.metric-box span').text('...');

    $.ajax({
        url: '/filter',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ year, school, major, method }),
        success: function (res) {
            $('#loading').hide();
            chartData = res.plot_html;

            $('#chart1').html(chartData.fig1);
            $('#chart2').html(chartData.fig2);
            $('#chart3').html(chartData.fig3);
            $('#chart4').html(chartData.fig4);

            $('#metric-count').text(res.metrics.total_records);
            $('#metric-avg').text(res.metrics.avg_score);
            $('#metric-schools').text(res.metrics.num_schools);
            $('#metric-majors').text(res.metrics.num_majors);

            $('#tab2, #tab3, #tab4').attr('data-loaded', 'false');
            Plotly.Plots.resize(document.getElementById('chart1'));
            AOS.refresh();
        },
        error: function () {
            $('#loading').hide();
            alert("❌ Lỗi khi lọc dữ liệu.");
        }
    });
}
$('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
    const targetId = $(e.target).attr('href').replace('#', '');
    const chartId = 'chart' + targetId.replace('tab', '');
    const tabContent = document.getElementById('tab' + chartId.charAt(chartId.length - 1));
    if (tabContent && tabContent.getAttribute('data-loaded') === 'false') {
        $('#' + chartId).html(chartData['fig' + chartId.charAt(chartId.length - 1)]);
        Plotly.Plots.resize(chartId);
        tabContent.setAttribute('data-loaded', 'true');
        AOS.refresh();
    } else {
        Plotly.Plots.resize(chartId);
    }
});