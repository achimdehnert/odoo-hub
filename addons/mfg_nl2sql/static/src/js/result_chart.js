/** @odoo-module **/
import { Component, useRef, onMounted, onWillUpdateProps, onWillUnmount } from "@odoo/owl";

export class ResultChart extends Component {
    static template = "mfg_nl2sql.ResultChart";
    static props = {
        chartConfig: { type: Object },
        chartType: { type: String },
    };

    setup() {
        this.canvasRef = useRef("chartCanvas");
        this.chart = null;

        onMounted(() => {
            this._renderChart(this.props.chartConfig);
        });

        onWillUpdateProps((nextProps) => {
            this._renderChart(nextProps.chartConfig);
        });

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        });
    }

    _renderChart(config) {
        if (!config || !config.data) return;
        if (!this.canvasRef.el) return;

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = this.canvasRef.el.getContext("2d");
        try {
            this.chart = new Chart(ctx, {
                type: config.type || "bar",
                data: config.data,
                options: {
                    ...config.options,
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 600,
                        easing: "easeOutQuart",
                    },
                    plugins: {
                        ...(config.options?.plugins || {}),
                        tooltip: {
                            backgroundColor: "rgba(15, 23, 42, 0.9)",
                            titleFont: { size: 13, weight: "600" },
                            bodyFont: { size: 12 },
                            padding: 12,
                            cornerRadius: 8,
                        },
                    },
                },
            });
        } catch (err) {
            console.error("Chart rendering error:", err);
        }
    }
}
