import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class VisualizationAgent:

    def __init__(self, output_dir="agents/charts"):

        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        print("Charts will be saved to:", self.output_dir)

    # --------------------------------------------------
    # Generic Series Chart
    # --------------------------------------------------

    def _plot_series(self, series, name):

        series = series.copy()

        try:
            series.index = pd.to_datetime(series.index)
        except:
            pass

        plt.figure(figsize=(8,5))
        plt.plot(series.index, series.values, marker="o")

        plt.title(name.replace("_", " ").title())
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.grid(True)

        filepath = os.path.join(self.output_dir, f"{name}.png")

        print("Attempting to save chart to:", filepath)

        plt.tight_layout()
        plt.savefig(filepath, dpi=300)
        plt.close()

        if os.path.exists(filepath):
            print("Chart successfully saved:", filepath)
        else:
            print("WARNING: Chart failed to save")

        return filepath


    # --------------------------------------------------
    # DataFrame Chart
    # --------------------------------------------------

    def _plot_dataframe(self, df, name):

        plt.figure(figsize=(8,5))

        df.plot()

        plt.title(name.replace("_", " ").title())

        filepath = os.path.join(self.output_dir, f"{name}.png")

        plt.tight_layout()
        plt.savefig(filepath, dpi=300)
        plt.close()

        return filepath


    # --------------------------------------------------
    # Auto Visualization Engine
    # --------------------------------------------------

    def generate_from_results(self, raw_results):
        """
        raw_results = original pandas outputs from analytics agent
        """

        charts = {}

        for tool_name, result in raw_results.items():

            try:

                # -------------------------------
                # Series
                # -------------------------------
                if isinstance(result, pd.Series):
                    if not result.empty:   # <-- check here
                        chart_path = self._plot_series(result, tool_name)
                        charts[tool_name] = chart_path

                # -------------------------------
                # DataFrame
                # -------------------------------
                elif isinstance(result, pd.DataFrame):
                    if not result.empty:   # <-- check here
                        chart_path = self._plot_dataframe(result, tool_name)
                        charts[tool_name] = chart_path

            except Exception as e:
                print(f"Visualization failed for {tool_name}: {e}")

        return charts