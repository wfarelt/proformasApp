(function () {
    const reportDataElement = document.getElementById('proforma-report-data');
    if (!reportDataElement) {
        return;
    }

    const reportData = JSON.parse(reportDataElement.textContent);

    const sellerValueLabelsPlugin = {
        id: 'sellerValueLabelsPlugin',
        afterDatasetsDraw(chart) {
            const dataset = chart.data.datasets[0];
            if (!dataset || !dataset.data || dataset.data.length === 0) {
                return;
            }

            const ctx = chart.ctx;
            const meta = chart.getDatasetMeta(0);

            ctx.save();
            ctx.font = '600 12px Arial';
            ctx.fillStyle = '#1f2937';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            meta.data.forEach((bar, index) => {
                const rawValue = Number(dataset.data[index] || 0);
                const label = '$ ' + rawValue.toLocaleString('en-US', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2
                });
                ctx.fillText(label, bar.x, bar.y - 6);
            });

            ctx.restore();
        }
    };

    const monthCtx = document.getElementById('chartMonthDailyExecuted');
    if (monthCtx) {
        new Chart(monthCtx, {
            type: 'line',
            data: {
                labels: reportData.month_labels,
                datasets: [{
                    label: 'Monto neto ejecutado por dia',
                    data: reportData.month_amounts,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.25,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 12,
                        right: 8,
                        top: 8,
                        bottom: 0
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            font: {
                                size: 13,
                                weight: '600'
                            },
                            callback: function(value) {
                                return '$ ' + Number(value).toLocaleString('en-US', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                });
                            }
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 11
                            }
                        }
                    }
                }
            }
        });
    }

    const sellerCtx = document.getElementById('chartTodaySalesBySeller');
    if (sellerCtx) {
        new Chart(sellerCtx, {
            type: 'bar',
            plugins: [sellerValueLabelsPlugin],
            data: {
                labels: reportData.seller_labels,
                datasets: [{
                    label: 'Monto neto ejecutado',
                    data: reportData.seller_sales,
                    backgroundColor: 'rgba(40, 167, 69, 0.6)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$ ' + Number(value).toLocaleString('en-US', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                });
                            }
                        }
                    }
                }
            }
        });
    }

    const filterForm = document.querySelector('form[method="get"]');
    const fechaInicioInput = document.getElementById('fecha_inicio');
    const fechaFinInput = document.getElementById('fecha_fin');
    if (filterForm && fechaInicioInput && fechaFinInput) {
        filterForm.addEventListener('submit', function (ev) {
            if (fechaInicioInput.value && fechaFinInput.value && fechaInicioInput.value >= fechaFinInput.value) {
                ev.preventDefault();
                alert('La fecha inicio debe ser menor que la fecha fin.');
            }
        });
    }

    if (reportData.print_mode) {
        window.setTimeout(function () {
            window.print();
        }, 250);
    }
})();
