import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
from loguru import logger
from pathlib import Path

class GraphGenerator:
    @staticmethod
    def _create_cfd_plots(df: pd.DataFrame, output_dir: str):
        figs = {}
        cols = [c.lower() for c in df.columns]
        
        # Convergence Plot (Iteration vs Residuals)
        iter_col = next((c for c in df.columns if 'iter' in c.lower() or 'step' in c.lower()), None)
        res_cols = [c for c in df.columns if 'res' in c.lower() or 'err' in c.lower()]
        if iter_col and res_cols:
            figs['cfd_convergence'] = px.line(df, x=iter_col, y=res_cols, title="XY Convergence Plot (Residuals)")
            
        # Contour/Scatter approximations (Pressure/Velocity)
        x_col = next((c for c in df.columns if c.lower() in ['x', 'pos_x', 'x_coord']), None)
        y_col = next((c for c in df.columns if c.lower() in ['y', 'pos_y', 'y_coord']), None)
        val_col = next((c for c in df.columns if 'press' in c.lower() or 'vel' in c.lower() or 'temp' in c.lower()), None)
        
        if x_col and y_col and val_col:
            figs['cfd_contour'] = px.scatter(df, x=x_col, y=y_col, color=val_col, title=f"Contour Approximation: {val_col.title()}")
            
        # 3D visualization if z exists
        z_col = next((c for c in df.columns if c.lower() in ['z', 'pos_z', 'z_coord']), None)
        if x_col and y_col and z_col and val_col:
            figs['cfd_3d_domain'] = px.scatter_3d(df, x=x_col, y=y_col, z=z_col, color=val_col, title="3D Fluid Domain Visualization")
            
        return figs

    @staticmethod
    def _create_fea_plots(df: pd.DataFrame, output_dir: str):
        figs = {}
        
        x_col = next((c for c in df.columns if c.lower() in ['x', 'node_x']), None)
        y_col = next((c for c in df.columns if c.lower() in ['y', 'node_y']), None)
        z_col = next((c for c in df.columns if c.lower() in ['z', 'node_z']), None)
        stress_col = next((c for c in df.columns if 'stress' in c.lower() or 'mises' in c.lower()), None)
        disp_col = next((c for c in df.columns if 'disp' in c.lower() or 'deflect' in c.lower()), None)
        fos_col = next((c for c in df.columns if 'fos' in c.lower() or 'safety' in c.lower() or 'margin' in c.lower()), None)
        
        if x_col and y_col and stress_col:
            figs['fea_stress_contour'] = px.scatter(df, x=x_col, y=y_col, color=stress_col, title="Von Mises Stress Contours")
        if x_col and y_col and disp_col:
            figs['fea_displacement'] = px.scatter(df, x=x_col, y=y_col, color=disp_col, title="Displacement/Deflection Plot")
        if x_col and y_col and fos_col:
            figs['fea_fos_map'] = px.scatter(df, x=x_col, y=y_col, color=fos_col, title="Factor of Safety (FOS) Map")
            
        return figs

    @staticmethod
    def _create_dem_plots(df: pd.DataFrame, output_dir: str):
        figs = {}
        
        x_col = next((c for c in df.columns if 'lon' in c.lower() or 'x' in c.lower() or 'east' in c.lower()), None)
        y_col = next((c for c in df.columns if 'lat' in c.lower() or 'y' in c.lower() or 'north' in c.lower()), None)
        elev_col = next((c for c in df.columns if 'elev' in c.lower() or 'z' in c.lower() or 'height' in c.lower()), None)
        slope_col = next((c for c in df.columns if 'slope' in c.lower() or 'grad' in c.lower()), None)
        
        if x_col and y_col and elev_col:
            figs['dem_elevation'] = px.scatter(df, x=x_col, y=y_col, color=elev_col, title="Terrain Elevation Map")
        if x_col and y_col and slope_col:
            figs['dem_slope'] = px.scatter(df, x=x_col, y=y_col, color=slope_col, title="Slope Steepness Map")
            
        return figs

    @staticmethod
    def _create_efd_plots(df: pd.DataFrame, output_dir: str):
        figs = {}
        
        time_col = next((c for c in df.columns if 'time' in c.lower() or 'date' in c.lower() or 'hour' in c.lower()), None)
        sales_col = next((c for c in df.columns if 'sale' in c.lower() or 'amount' in c.lower() or 'revenue' in c.lower()), None)
        tax_col = next((c for c in df.columns if 'tax' in c.lower() or 'vat' in c.lower()), None)
        void_col = next((c for c in df.columns if 'void' in c.lower() or 'cancel' in c.lower() or 'error' in c.lower()), None)
        method_col = next((c for c in df.columns if 'method' in c.lower() or 'payment' in c.lower() or 'type' in c.lower()), None)
        machine_col = next((c for c in df.columns if 'machine' in c.lower() or 'device' in c.lower() or 'efd' in c.lower()), None)

        if time_col and sales_col:
            # Hourly/Daily Sales Trends
            try:
                trend_df = df.groupby(time_col)[sales_col].sum().reset_index()
                figs['efd_sales_trend'] = px.line(trend_df, x=time_col, y=sales_col, title="Sales Trends Over Time")
            except: pass
            
        if method_col and sales_col:
            # Payment Method Distribution
            try:
                method_df = df.groupby(method_col)[sales_col].sum().reset_index()
                figs['efd_payment_dist'] = px.pie(method_df, names=method_col, values=sales_col, title="Payment Method Distribution")
            except: pass
            
        if machine_col and sales_col:
            # Z-Report Aggregations
            try:
                z_df = df.groupby(machine_col)[[sales_col]].sum().reset_index()
                if tax_col:
                    z_df[tax_col] = df.groupby(machine_col)[tax_col].sum().values
                    figs['efd_z_report'] = px.bar(z_df, x=machine_col, y=[sales_col, tax_col], title="Z-Report Aggregations by Machine", barmode="stack")
                else:
                    figs['efd_z_report'] = px.bar(z_df, x=machine_col, y=sales_col, title="Z-Report Aggregations by Machine")
            except: pass
            
        if void_col:
            # Voids and Cancellations
            try:
                if machine_col:
                    void_df = df.groupby(machine_col)[void_col].sum().reset_index()
                    figs['efd_voids'] = px.bar(void_df, x=machine_col, y=void_col, title="Voids and Cancellations by Machine")
                else:
                    figs['efd_voids'] = px.histogram(df, x=void_col, title="Voids and Cancellations Distribution")
            except: pass

        return figs

    @staticmethod
    def create_service_visualizations(df: pd.DataFrame, output_dir: str, service: str):
        """Auto-generate service-specific plots or dynamic fallback"""
        logger.info(f"Generating {service} visualizations...")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        figs = {}
        srv = service.upper()
        if srv == "CFD":
            figs = GraphGenerator._create_cfd_plots(df, output_dir)
        elif srv == "FEA":
            figs = GraphGenerator._create_fea_plots(df, output_dir)
        elif srv == "DEM":
            figs = GraphGenerator._create_dem_plots(df, output_dir)
        elif srv == "EFD":
            figs = GraphGenerator._create_efd_plots(df, output_dir)
            
        # Fallback if specific plots couldn't be generated due to missing columns
        if not figs:
            logger.warning(f"Could not find specific columns for {srv}. Falling back to dynamic plotting.")
            figs = GraphGenerator._create_dynamic_plots_internal(df, srv)
            
        saved_paths = {}
        for name, fig in figs.items():
            try:
                png_path = f"{output_dir}/{name}.png"
                fig.write_image(png_path, engine="kaleido", width=800, height=500)
                saved_paths[name] = png_path
            except Exception as e:
                logger.error(f"Error saving {name}.png: {e}")
                
        return saved_paths

    @staticmethod
    def _create_dynamic_plots_internal(df: pd.DataFrame, prefix: str):
        figs = {}
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(num_cols) == 0:
            return figs
            
        x_col = next((c for c in df.columns if c.lower() in ['time', 'step', 'id', 'x', 'index']), None)
        if not x_col and len(num_cols) > 0:
            x_col = num_cols[0]
            
        y_cols = [c for c in num_cols if c != x_col][:3]
        if y_cols:
            try:
                figs[f'{prefix.lower()}_dynamic_line'] = px.line(df, x=x_col, y=y_cols, title=f"{prefix} Dynamic Line Plot")
            except: pass
                
        if len(num_cols) >= 3:
            try:
                figs[f'{prefix.lower()}_3d_scatter'] = px.scatter_3d(
                    df, x=num_cols[0], y=num_cols[1], z=num_cols[2], 
                    color=num_cols[2] if len(num_cols) > 2 else None,
                    title=f"{prefix} 3D Data Overview"
                )
            except: pass
                
        if len(num_cols) > 1:
            try:
                corr = df[num_cols].corr()
                figs[f'{prefix.lower()}_correlation'] = px.imshow(corr, text_auto=True, title=f"{prefix} Parameter Correlation Heatmap")
            except: pass

        if not figs and len(df) == 0:
            figs[f'{prefix.lower()}_sample'] = px.scatter(x=[1, 2, 3], y=[4, 5, 6], title="Sample Visualization (No Data)")
            
        return figs
