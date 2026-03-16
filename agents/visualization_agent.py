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

        # Determine if it's time series or categorical
        is_time_series = False
        try:
            pd.to_datetime(series.index)
            is_time_series = True
        except:
            pass

        # Adjust figure size based on number of items
        n_items = len(series)
        if n_items > 20:
            figsize = (14, 8)
        elif n_items > 10:
            figsize = (12, 6)
        else:
            figsize = (10, 6)

        plt.figure(figsize=figsize)

        if is_time_series:
            # Time series - use line plot
            plt.plot(series.index, series.values, marker="o")
            plt.xlabel("Time")
            plt.xticks(rotation=45, ha='right')
        else:
            # Categorical - use bar plot
            if n_items > 15:
                # Too many categories - use horizontal bar
                series = series.sort_values()
                plt.barh(range(n_items), series.values)
                plt.yticks(range(n_items), series.index, fontsize=8)
                plt.ylabel("Customer")
            else:
                # Few categories - use vertical bar
                plt.bar(series.index, series.values)
                plt.xticks(rotation=45, ha='right')
                plt.xlabel("Customer")

        plt.title(name.replace("_", " ").title())
        plt.ylabel("Revenue ($)")
        plt.grid(True)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{name}.png")
        
        # ADD THESE PRINT STATEMENTS
        print("Attempting to save chart to:", filepath)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        # ADD THIS CHECK
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