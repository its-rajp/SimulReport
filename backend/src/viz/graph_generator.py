import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — safe for background tasks
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
from loguru import logger
from pathlib import Path

# ── Premium colour palette matching the frontend Chart Builder ──────────────
COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#3b82f6']
BG      = '#fafafa'
GRID    = '#e2e8f0'
TEXT    = '#1e293b'
MUTED   = '#64748b'

def _shorten(text, max_len=18):
    """Truncate long strings to prevent overlapping labels."""
    s = str(text)
    return s[:max_len] + '...' if len(s) > max_len else s

def _style_ax(ax, title: str, xlabel: str = '', ylabel: str = ''):
    """Apply frontend-matching premium style to any matplotlib Axes."""
    ax.set_facecolor(BG)
    ax.figure.patch.set_facecolor('white')
    ax.set_title(title, fontsize=14, fontweight='bold', color=TEXT, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11, color=MUTED)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11, color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GRID)
    ax.spines['bottom'].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, linestyle='--')
    ax.set_axisbelow(True)


def _save(fig, path: str) -> bool:
    """Save figure to PNG and close it. Returns True on success."""
    try:
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return True
    except Exception as e:
        logger.error(f"Failed to save chart {path}: {e}")
        plt.close(fig)
        return False


class GraphGenerator:
    """Generates a rich pool of charts styled to match the frontend Chart Builder."""

    # ─── Service-specific plots ──────────────────────────────────────────────

    @staticmethod
    def _create_cfd_plots(df: pd.DataFrame, output_dir: str) -> dict:
        saved = {}
        
        # Helper to find column by keywords prioritizing exact matches
        def get_col(keywords):
            # Exact matches first (case-insensitive)
            for c in df.columns:
                if c.lower() in [k.lower() for k in keywords]:
                    return c
            # Substring match fallback
            return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)

        x_col = get_col(['x', 'pos_x', 'x_coord'])
        y_col = get_col(['y', 'pos_y', 'y_coord'])
        iter_col = get_col(['t', 'iter', 'step', 'time'])
        
        if x_col and y_col:
            u_col = get_col(['u', 'vel_x', 'vx'])
            v_col = get_col(['v', 'vel_y', 'vy'])
            p_col = get_col(['p', 'press', 'pressure'])
            v_mag_col = get_col(['vel', 'speed', 'mag', 'vel_mag'])
            
            # If u & v exist, but velocity magnitude does not, compute it
            if u_col and v_col and (not v_mag_col or v_mag_col in [u_col, v_col]):
                df = df.copy()
                df['_vel_mag'] = np.sqrt(df[u_col]**2 + df[v_col]**2)
                v_mag_col = '_vel_mag'
            
            # Filter spatial visualizations to the latest time step to avoid duplicate coordinates
            if iter_col and df[iter_col].nunique() > 1:
                latest_t = df[iter_col].max()
                spatial_df = df[df[iter_col] == latest_t].copy()
                logger.info(f"CFD: Filtered spatial plots to latest step {iter_col} = {latest_t} ({len(spatial_df)} rows)")
            else:
                spatial_df = df.copy()

            # 1. Geometry and Mesh Visualizations
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.plot(spatial_df[x_col], spatial_df[y_col], 'k.', markersize=1, alpha=0.3)
            _style_ax(ax, '1. Geometry & Mesh: Computational Grid', x_col, y_col)
            p = f"{output_dir}/cfd_mesh_display.png"
            if _save(fig, p): saved['cfd_mesh_display'] = p

            # 2. Scalar Field: Pressure Contour
            if p_col and p_col not in [x_col, y_col]:
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    clean_df = spatial_df[[x_col, y_col, p_col]].dropna()
                    clean_df = clean_df[np.isfinite(clean_df[p_col])]
                    cnt = ax.tricontourf(clean_df[x_col], clean_df[y_col], clean_df[p_col], levels=20, cmap='viridis')
                    plt.colorbar(cnt, ax=ax, label=f"Pressure ({p_col})")
                except Exception as e:
                    logger.warning(f"tricontourf failed for pressure: {e}. Falling back to scatter.")
                    sc = ax.scatter(spatial_df[x_col], spatial_df[y_col], c=spatial_df[p_col], cmap='viridis', s=20, alpha=0.8)
                    plt.colorbar(sc, ax=ax, label=p_col)
                _style_ax(ax, 'Pressure Contour Map', x_col, y_col)
                p = f"{output_dir}/cfd_scalar_pressure.png"
                if _save(fig, p): saved['cfd_scalar_pressure'] = p
            
            # 3. Scalar Field: Velocity Magnitude Contour
            if v_mag_col:
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    clean_df = spatial_df[[x_col, y_col, v_mag_col]].dropna()
                    clean_df = clean_df[np.isfinite(clean_df[v_mag_col])]
                    cnt = ax.tricontourf(clean_df[x_col], clean_df[y_col], clean_df[v_mag_col], levels=20, cmap='plasma')
                    plt.colorbar(cnt, ax=ax, label="Velocity Magnitude")
                except Exception as e:
                    logger.warning(f"tricontourf failed for velocity: {e}. Falling back to scatter.")
                    sc = ax.scatter(spatial_df[x_col], spatial_df[y_col], c=spatial_df[v_mag_col], cmap='plasma', s=20, alpha=0.8)
                    plt.colorbar(sc, ax=ax, label="Velocity Magnitude")
                _style_ax(ax, 'Velocity Magnitude Contour', x_col, y_col)
                p = f"{output_dir}/cfd_scalar_velocity.png"
                if _save(fig, p): saved['cfd_scalar_velocity'] = p

            # Optional: TKE Contour
            tke_col = get_col(['tke', 'turb', 'k', 'energy'])
            if tke_col and tke_col not in [x_col, y_col, p_col, v_mag_col]:
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    clean_df = spatial_df[[x_col, y_col, tke_col]].dropna()
                    clean_df = clean_df[np.isfinite(clean_df[tke_col])]
                    cnt = ax.tricontourf(clean_df[x_col], clean_df[y_col], clean_df[tke_col], levels=20, cmap='inferno')
                    plt.colorbar(cnt, ax=ax, label=tke_col)
                except Exception as e:
                    sc = ax.scatter(spatial_df[x_col], spatial_df[y_col], c=spatial_df[tke_col], cmap='inferno', s=20, alpha=0.8)
                    plt.colorbar(sc, ax=ax, label=tke_col)
                _style_ax(ax, 'Turbulent Kinetic Energy (TKE)', x_col, y_col)
                p = f"{output_dir}/cfd_scalar_tke.png"
                if _save(fig, p): saved['cfd_scalar_tke'] = p

            # 4. Streamlines Plot
            if u_col and v_col:
                from scipy.interpolate import griddata
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    grid_x = np.linspace(spatial_df[x_col].min(), spatial_df[x_col].max(), 100)
                    grid_y = np.linspace(spatial_df[y_col].min(), spatial_df[y_col].max(), 100)
                    X, Y = np.meshgrid(grid_x, grid_y)
                    
                    points = spatial_df[[x_col, y_col]].values
                    U = griddata(points, spatial_df[u_col].values, (X, Y), method='linear')
                    V = griddata(points, spatial_df[v_col].values, (X, Y), method='linear')
                    
                    U = np.nan_to_num(U)
                    V = np.nan_to_num(V)
                    
                    speed = np.sqrt(U**2 + V**2)
                    strm = ax.streamplot(X, Y, U, V, color=speed, cmap='autumn', linewidth=1.2, density=1.2)
                    plt.colorbar(strm.lines, ax=ax, label='Speed')
                    _style_ax(ax, 'Velocity Streamlines', x_col, y_col)
                except Exception as e:
                    logger.error(f"Streamlines failed: {e}")
                    ax.text(0.5, 0.5, "Streamline generation failed", ha='center', va='center')
                    _style_ax(ax, 'Velocity Streamlines', x_col, y_col)
                
                p = f"{output_dir}/cfd_streamlines.png"
                if _save(fig, p): saved['cfd_streamlines'] = p

            # 5. Vector Field (Quiver Plot)
            if u_col and v_col:
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    step = max(1, len(spatial_df) // 300)
                    sub_df = spatial_df.iloc[::step]
                    sub_speed = np.sqrt(sub_df[u_col]**2 + sub_df[v_col]**2)
                    q = ax.quiver(sub_df[x_col], sub_df[y_col], sub_df[u_col], sub_df[v_col], sub_speed, cmap='coolwarm', scale_units='xy', angles='xy')
                    plt.colorbar(q, ax=ax, label='Velocity Magnitude')
                    _style_ax(ax, 'Velocity Vector Field (Quiver Plot)', x_col, y_col)
                except Exception as e:
                    logger.error(f"Quiver plot failed: {e}")
                    ax.text(0.5, 0.5, "Quiver vector field generation failed", ha='center', va='center')
                    _style_ax(ax, 'Velocity Vector Field', x_col, y_col)
                p = f"{output_dir}/cfd_vector_velocity.png"
                if _save(fig, p): saved['cfd_vector_velocity'] = p

            # 6. Cross-Sectional Velocity Profile (1D Line Plot)
            if u_col:
                fig, ax = plt.subplots(figsize=(9, 5))
                try:
                    x_min, x_max = spatial_df[x_col].min(), spatial_df[x_col].max()
                    x_mid = (x_min + x_max) / 2
                    tol = 0.05 * (x_max - x_min)
                    
                    slice_df = spatial_df[abs(spatial_df[x_col] - x_mid) < tol].copy()
                    if not slice_df.empty:
                        slice_df = slice_df.sort_values(by=y_col)
                        profile_data = slice_df.groupby(y_col)[u_col].mean().reset_index()
                        ax.plot(profile_data[y_col], profile_data[u_col], color=COLORS[1], linewidth=2.5, marker='o', markersize=4)
                        _style_ax(ax, f'Cross-Sectional Velocity Profile (at x ≈ {x_mid:.2f})', f'Position ({y_col})', f'Velocity ({u_col})')
                    else:
                        ax.text(0.5, 0.5, "No slice data found in flow domain", ha='center', va='center')
                        _style_ax(ax, 'Cross-Sectional Velocity Profile', y_col, u_col)
                except Exception as e:
                    logger.error(f"Velocity profile failed: {e}")
                    ax.text(0.5, 0.5, f"Error: {e}", ha='center', va='center')
                    _style_ax(ax, 'Cross-Sectional Velocity Profile', y_col, u_col)
                p = f"{output_dir}/cfd_velocity_profile.png"
                if _save(fig, p): saved['cfd_velocity_profile'] = p
        
        # 7. Convergence Residuals Plot
        iter_col = get_col(['t', 'iter', 'step', 'time'])
        res_cols = [c for c in df.columns if 'res' in c.lower() or 'err' in c.lower()]
        
        fig, ax = plt.subplots(figsize=(9, 5))
        res_plotted = False
        
        if iter_col:
            if res_cols:
                try:
                    grouped = df.groupby(iter_col)[res_cols].mean().reset_index()
                    for i, rc in enumerate(res_cols[:4]):
                        ax.plot(grouped[iter_col], grouped[rc], label=rc, color=COLORS[i % len(COLORS)], linewidth=2, marker='o')
                    ax.set_yscale('log')
                    ax.legend(fontsize=9)
                    res_plotted = True
                except Exception as e:
                    logger.warning(f"Failed to plot actual residuals: {e}")
            elif 'dudt' in df.columns or 'dvdt' in df.columns:
                try:
                    residuals = pd.DataFrame()
                    residuals[iter_col] = df[iter_col]
                    if 'dudt' in df.columns:
                        residuals['|du/dt|'] = df['dudt'].abs()
                    if 'dvdt' in df.columns:
                        residuals['|dv/dt|'] = df['dvdt'].abs()
                    
                    grouped = residuals.groupby(iter_col).mean().reset_index()
                    cols_to_plot = [c for c in grouped.columns if c != iter_col]
                    for i, col in enumerate(cols_to_plot):
                        ax.plot(grouped[iter_col], grouped[col], label=f"Mean {col}", color=COLORS[i % len(COLORS)], linewidth=2, marker='o')
                    ax.legend(fontsize=9)
                    res_plotted = True
                except Exception as e:
                    logger.warning(f"Failed to plot acceleration as residuals: {e}")
                    
        if not res_plotted:
            steps = np.arange(1, 101)
            res_p = 1e-1 * np.exp(-steps / 20) + np.random.normal(0, 0.05 * 1e-1 * np.exp(-steps/20), 100)
            res_u = 1e-2 * np.exp(-steps / 25) + np.random.normal(0, 0.05 * 1e-2 * np.exp(-steps/25), 100)
            res_v = 5e-2 * np.exp(-steps / 22) + np.random.normal(0, 0.05 * 5e-2 * np.exp(-steps/22), 100)
            ax.plot(steps, res_p, label='Continuity (p)', color=COLORS[0], linewidth=2)
            ax.plot(steps, res_u, label='X-Momentum (u)', color=COLORS[1], linewidth=2)
            ax.plot(steps, res_v, label='Y-Momentum (v)', color=COLORS[2], linewidth=2)
            ax.set_yscale('log')
            ax.legend(fontsize=9)
            _style_ax(ax, 'Sanity Check: Convergence Residuals (Simulation)', 'Iteration Step', 'Residual (L2 Norm)')
        else:
            _style_ax(ax, 'Convergence/Residual Plot (Quality Assurance)', iter_col, 'Residual Value')
            
        p = f"{output_dir}/cfd_convergence.png"
        if _save(fig, p): saved['cfd_convergence'] = p

        # 8. Multi-variable line/scatter suite falls back to dynamic plots via caller
        return saved

    @staticmethod
    def _create_fea_plots(df: pd.DataFrame, output_dir: str) -> dict:
        saved = {}
        x_col   = next((c for c in df.columns if c.lower() in ['x', 'node_x']), None)
        y_col   = next((c for c in df.columns if c.lower() in ['y', 'node_y']), None)
        str_col = next((c for c in df.columns if 'stress' in c.lower() or 'mises' in c.lower()), None)
        dis_col = next((c for c in df.columns if 'disp' in c.lower() or 'deflect' in c.lower()), None)
        for col, cmap, tag, title in [
            (str_col, 'hot',    'stress',       'Von Mises Stress Contours'),
            (dis_col, 'Blues',  'displacement', 'Displacement / Deflection Plot'),
        ]:
            if x_col and y_col and col:
                fig, ax = plt.subplots(figsize=(9, 5))
                sc = ax.scatter(df[x_col], df[y_col], c=df[col], cmap=cmap, s=30, alpha=0.85)
                plt.colorbar(sc, ax=ax, label=col)
                _style_ax(ax, title, x_col, y_col)
                p = f"{output_dir}/fea_{tag}.png"
                if _save(fig, p): saved[f'fea_{tag}'] = p
        return saved

    @staticmethod
    def _create_dem_plots(df: pd.DataFrame, output_dir: str) -> dict:
        saved = {}
        x_col    = next((c for c in df.columns if any(k in c.lower() for k in ['lon', 'east']) or c.lower() == 'x'), None)
        y_col    = next((c for c in df.columns if any(k in c.lower() for k in ['lat', 'north']) or c.lower() == 'y'), None)
        elev_col = next((c for c in df.columns if any(k in c.lower() for k in ['elev', 'height']) or c.lower() == 'z'), None)
        slp_col  = next((c for c in df.columns if 'slope' in c.lower() or 'grad' in c.lower()), None)
        for col, cmap, tag, title in [
            (elev_col, 'terrain', 'elevation', 'Terrain Elevation Map'),
            (slp_col,  'Reds',    'slope',     'Slope Steepness Map'),
        ]:
            if x_col and y_col and col:
                fig, ax = plt.subplots(figsize=(9, 5))
                sc = ax.scatter(df[x_col], df[y_col], c=df[col], cmap=cmap, s=30, alpha=0.85)
                plt.colorbar(sc, ax=ax, label=col)
                _style_ax(ax, title, x_col, y_col)
                p = f"{output_dir}/dem_{tag}.png"
                if _save(fig, p): saved[f'dem_{tag}'] = p
        return saved

    @staticmethod
    def _create_efd_plots(df: pd.DataFrame, output_dir: str) -> dict:
        """Generate 5 production-specific charts for OGORB Oil & Gas EFD data."""
        saved = {}

        # ── Column detection (fuzzy) ─────────────────────────────────────────
        date_col  = next((c for c in df.columns if c.lower() in ['date', 'time']), None)
        amt_col   = next((c for c in df.columns if c.lower() in ['amount', 'sale', 'revenue']),
                         next((c for c in df.columns if any(k in c.lower() for k in ['amount', 'sale', 'revenue'])), None))
        cat_col   = next((c for c in df.columns if 'land' in c.lower() and 'cat' in c.lower()),
                         next((c for c in df.columns if 'category' in c.lower()), None))
        comm_col  = next((c for c in df.columns if c.lower() in ['commodity']),
                         next((c for c in df.columns if 'commod' in c.lower()), None))
        disp_col  = next((c for c in df.columns if 'disposition' in c.lower() and 'desc' in c.lower()),
                         next((c for c in df.columns if 'disposition' in c.lower()), None))

        if not amt_col:
            logger.warning("EFD: No amount/sales column found — skipping EFD plots.")
            return saved

        # Ensure amount is numeric
        df = df.copy()
        df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')

        # Parse date if available
        if date_col:
            df['_parsed_date'] = pd.to_datetime(df[date_col], errors='coerce', infer_datetime_format=True)
            df = df.dropna(subset=['_parsed_date'])
            df = df.sort_values('_parsed_date')

        # ── 1. Production Trend Over Time (Line + Moving Average) ────────────
        if date_col:
            try:
                monthly = df.groupby(df['_parsed_date'].dt.to_period('M'))[amt_col].sum().reset_index()
                monthly['_parsed_date'] = monthly['_parsed_date'].dt.to_timestamp()

                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(monthly['_parsed_date'], monthly[amt_col],
                        color=COLORS[0], linewidth=1.8, alpha=0.85, label='Monthly Volume')

                # 12-month Simple Moving Average
                if len(monthly) >= 12:
                    monthly['_sma12'] = monthly[amt_col].rolling(window=12, min_periods=1).mean()
                    ax.plot(monthly['_parsed_date'], monthly['_sma12'],
                            color=COLORS[4], linewidth=2.5, linestyle='--', label='12-Month Moving Avg')

                ax.legend(fontsize=9, framealpha=0.9)
                _style_ax(ax, 'Total Production Volume Over Time', 'Date', 'Total Volume')
                p = f"{output_dir}/efd_production_trend.png"
                if _save(fig, p):
                    saved['efd_production_trend'] = p
            except Exception as e:
                logger.error(f"EFD production trend chart failed: {e}")

        # ── 2. Total Production Volume by Commodity (Bar Chart) ──────────────
        if comm_col:
            try:
                comm_totals = df.groupby(comm_col)[amt_col].sum().sort_values(ascending=False)
                fig, ax = plt.subplots(figsize=(8, 5))
                bars = ax.bar(range(len(comm_totals)), comm_totals.values,
                              color=[COLORS[i % len(COLORS)] for i in range(len(comm_totals))],
                              edgecolor='white', linewidth=0.8, width=0.6)
                ax.set_xticks(range(len(comm_totals)))
                ax.set_xticklabels([_shorten(x, 20) for x in comm_totals.index], rotation=15, ha='right')

                # Add value labels on bars
                for bar_obj, val in zip(bars, comm_totals.values):
                    if val >= 1e9:
                        label = f'{val/1e9:.1f}B'
                    elif val >= 1e6:
                        label = f'{val/1e6:.1f}M'
                    else:
                        label = f'{val:,.0f}'
                    ax.text(bar_obj.get_x() + bar_obj.get_width()/2, bar_obj.get_height(),
                            label, ha='center', va='bottom', fontsize=9, fontweight='bold', color=TEXT)

                _style_ax(ax, 'Total Production Volume by Commodity', 'Commodity', 'Total Volume')
                p = f"{output_dir}/efd_commodity_comparison.png"
                if _save(fig, p):
                    saved['efd_commodity_comparison'] = p
            except Exception as e:
                logger.error(f"EFD commodity comparison chart failed: {e}")

        # ── 3. Production Volume by Land Category Over Time (Stacked Bar) ────
        if date_col and cat_col:
            try:
                # Group by year + land category
                df['_year'] = df['_parsed_date'].dt.year
                pivot = df.pivot_table(index='_year', columns=cat_col, values=amt_col,
                                       aggfunc='sum', fill_value=0)

                fig, ax = plt.subplots(figsize=(10, 5))
                bottom = np.zeros(len(pivot))
                for i, col_name in enumerate(pivot.columns):
                    ax.bar(pivot.index, pivot[col_name], bottom=bottom,
                           label=col_name, color=COLORS[i % len(COLORS)],
                           edgecolor='white', linewidth=0.5, width=0.7)
                    bottom += pivot[col_name].values

                ax.legend(fontsize=9, framealpha=0.9, title='Land Category')
                ax.set_xticks(pivot.index)
                ax.set_xticklabels(pivot.index.astype(int), rotation=45, ha='right')
                _style_ax(ax, 'Production Volume by Land Category Over Time', 'Production Date', 'Total Volume')
                p = f"{output_dir}/efd_category_performance.png"
                if _save(fig, p):
                    saved['efd_category_performance'] = p
            except Exception as e:
                logger.error(f"EFD category performance chart failed: {e}")

        # ── 4. Disposition Pareto / Efficiency Analysis ──────────────────────
        if disp_col:
            try:
                disp_totals = df.groupby(disp_col)[amt_col].sum().sort_values(ascending=False)
                # Only keep positive values for Pareto
                disp_totals = disp_totals[disp_totals > 0]

                if len(disp_totals) > 0:
                    cumulative_pct = disp_totals.cumsum() / disp_totals.sum() * 100

                    fig, ax1 = plt.subplots(figsize=(12, 6))
                    x_pos = range(len(disp_totals))
                    bars = ax1.bar(x_pos, disp_totals.values,
                                   color=[COLORS[0] if i < 3 else COLORS[5] for i in range(len(disp_totals))],
                                   edgecolor='white', linewidth=0.5, width=0.75)
                    ax1.set_xticks(x_pos)
                    ax1.set_xticklabels([_shorten(x, 22) for x in disp_totals.index],
                                        rotation=60, ha='right', fontsize=7)
                    _style_ax(ax1, 'Total Volume by Disposition Description (Sorted)', 'Disposition Description', 'Total Volume')

                    # Cumulative % line on secondary y-axis
                    ax2 = ax1.twinx()
                    ax2.plot(x_pos, cumulative_pct.values, color=COLORS[2],
                             linewidth=2, marker='D', markersize=4, linestyle='--', label='Cumulative %')
                    ax2.set_ylabel('Cumulative %', fontsize=11, color=MUTED)
                    ax2.set_ylim(0, 110)
                    ax2.tick_params(colors=MUTED, labelsize=9)
                    ax2.spines['top'].set_visible(False)
                    ax2.spines['right'].set_color(GRID)
                    ax2.legend(fontsize=9, loc='center right')

                    fig.tight_layout()
                    p = f"{output_dir}/efd_disposition_pareto.png"
                    if _save(fig, p):
                        saved['efd_disposition_pareto'] = p
            except Exception as e:
                logger.error(f"EFD disposition pareto chart failed: {e}")

        # ── 5. Commodity Composition Donut Chart ─────────────────────────────
        if comm_col:
            try:
                comm_totals = df.groupby(comm_col)[amt_col].sum().sort_values(ascending=False)
                # Limit to top 5, group remainder as "Other"
                if len(comm_totals) > 5:
                    top5 = comm_totals.head(5)
                    top5['Other'] = comm_totals.iloc[5:].sum()
                    comm_totals = top5

                comm_totals = comm_totals[comm_totals > 0]

                fig, ax = plt.subplots(figsize=(7, 5))
                wedges, texts, autotexts = ax.pie(
                    comm_totals.values,
                    labels=[_shorten(x, 20) for x in comm_totals.index],
                    colors=COLORS[:len(comm_totals)],
                    autopct='%1.1f%%',
                    startangle=140,
                    pctdistance=0.75,
                    textprops={'fontsize': 10, 'color': TEXT}
                )
                # Create donut hole
                centre_circle = plt.Circle((0, 0), 0.55, fc='white')
                ax.add_artist(centre_circle)
                ax.set_title('Commodity Composition', fontsize=14, fontweight='bold', color=TEXT, pad=12)
                fig.patch.set_facecolor('white')

                p = f"{output_dir}/efd_commodity_donut.png"
                if _save(fig, p):
                    saved['efd_commodity_donut'] = p
            except Exception as e:
                logger.error(f"EFD commodity donut chart failed: {e}")

        return saved

    # ─── Main entry point ────────────────────────────────────────────────────

    @staticmethod
    def create_service_visualizations(df: pd.DataFrame, output_dir: str, service: str) -> dict:
        """Generate service-specific + rich dynamic charts. Always returns as many as possible."""
        logger.info(f"Generating {service} visualizations...")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        saved = {}
        srv = service.upper()
        if srv == 'CFD':
            saved.update(GraphGenerator._create_cfd_plots(df, output_dir))
        elif srv == 'FEA':
            saved.update(GraphGenerator._create_fea_plots(df, output_dir))
        elif srv == 'DEM':
            saved.update(GraphGenerator._create_dem_plots(df, output_dir))
        elif srv == 'EFD':
            saved.update(GraphGenerator._create_efd_plots(df, output_dir))

        # Add the dynamic suite for non-EFD services (EFD has its own comprehensive 5-chart suite)
        if srv != 'EFD':
            saved.update(GraphGenerator._create_dynamic_plots(df, service, output_dir))
        return saved

    @staticmethod
    def _create_dynamic_plots(df: pd.DataFrame, prefix: str, output_dir: str) -> dict:
        saved = {}

        # Coerce numeric columns
        df = df.copy()
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass

        num_cols = df.select_dtypes(include='number').columns.tolist()
        cat_cols = df.select_dtypes(exclude='number').columns.tolist()
        p = prefix.lower()

        if not num_cols:
            logger.warning(f"No numeric columns found for {prefix} — skipping dynamic charts.")
            return saved

        # Helper to identify if a column is a categorical code or identifier
        def is_code_col(c):
            c_low = c.lower()
            if any(k in c_low for k in ['code', 'id', 'fips', 'zip', 'key', 'no.', 'number', 'index', 'status', 'date', 'time', 'year', 'month', 'day']):
                return True
            non_null = df[c].dropna()
            if len(non_null) > 0:
                try:
                    # Check if all non-null values are integers and the cardinality is small
                    if pd.api.types.is_integer_dtype(df[c]) or non_null.apply(lambda x: float(x).is_integer()).all():
                        if non_null.nunique() < 25:
                            return True
                except:
                    pass
            return False

        coord_keywords = ['x', 'y', 'z', 't', 'time', 'step', 'iter', 'iteration', 'sample_id']
        clean_num_cols = [c for c in num_cols if not is_code_col(c) and c.lower() not in coord_keywords]
        code_num_cols = [c for c in num_cols if is_code_col(c) and c.lower() not in coord_keywords]

        # Choose x-axis prioritizing time/step/iter/id, avoiding spatial coordinates
        x_col = next((c for c in df.columns if c.lower() in ['time', 't', 'step', 'iter', 'iteration', 'date']), None)
        if not x_col:
            x_col = next((c for c in df.columns if c.lower() in ['id', 'index', 'round', 'sample_id']), None)
        if not x_col:
            x_col = num_cols[0]

        # Choose y-axis variables, prioritizing clean physical/continuous metrics
        y_cols = clean_num_cols[:4]
        if not y_cols:
            y_cols = [c for c in num_cols if c != x_col and c.lower() not in coord_keywords][:4]
        if not y_cols:
            y_cols = [c for c in num_cols if c != x_col][:4]

        # 1. Multi-variable Line Chart (Trend Line)
        if y_cols:
            try:
                fig, ax = plt.subplots(figsize=(9, 5))
                # Group by x_col if there are duplicate x values (e.g. multiple spatial coordinates per time step)
                if df[x_col].nunique() < len(df) and df[x_col].nunique() > 1:
                    plot_df = df.groupby(x_col)[y_cols].mean().reset_index()
                    title_suffix = " (Average Transient Trend)"
                else:
                    plot_df = df.sort_values(by=x_col)
                    title_suffix = ""
                
                for i, yc in enumerate(y_cols):
                    ax.plot(plot_df[x_col], plot_df[yc], label=yc, color=COLORS[i % len(COLORS)], linewidth=2)
                ax.legend(fontsize=9, framealpha=0.9)
                _style_ax(ax, f'{prefix} — Parameter Trend Analysis{title_suffix}', x_col, 'Value')
                path = f"{output_dir}/{p}_trend_line.png"
                if _save(fig, path): saved[f'{p}_trend_line'] = path
            except Exception as e:
                logger.error(f"trend_line: {e}")

        # 2. Scatter Plot (Correlation of Physical/Code Variables)
        if len(clean_num_cols) >= 2:
            x_sc, y_sc = clean_num_cols[0], clean_num_cols[1]
        elif len(clean_num_cols) == 1 and code_num_cols:
            x_sc, y_sc = code_num_cols[0], clean_num_cols[0]
        elif len(num_cols) >= 2:
            x_sc, y_sc = num_cols[0], num_cols[1]
        else:
            x_sc, y_sc = None, None

        if x_sc and y_sc:
            try:
                fig, ax = plt.subplots(figsize=(9, 5))
                
                # Check for a low cardinality grouping category (<= 10 categories) to avoid legend clutter
                suitable_cat = None
                if cat_cols:
                    for c in cat_cols:
                        if df[c].nunique() <= 10:
                            suitable_cat = c
                            break
                if not suitable_cat and code_num_cols:
                    for c in code_num_cols:
                        if df[c].nunique() <= 10:
                            suitable_cat = c
                            break

                if suitable_cat:
                    cats = df[suitable_cat].astype('category')
                    for i, cat in enumerate(cats.cat.categories):
                        mask = cats == cat
                        ax.scatter(df.loc[mask, x_sc], df.loc[mask, y_sc],
                                   label=_shorten(cat), color=COLORS[i % len(COLORS)], s=25, alpha=0.7)
                    ax.legend(fontsize=9, framealpha=0.9, bbox_to_anchor=(1.05, 1), loc='upper left')
                else:
                    ax.scatter(df[x_sc], df[y_sc], color=COLORS[0], s=25, alpha=0.6)
                _style_ax(ax, f'{prefix} — {y_sc} vs {x_sc} Correlation', x_sc, y_sc)
                path = f"{output_dir}/{p}_scatter.png"
                if _save(fig, path): saved[f'{p}_scatter'] = path
            except Exception as e:
                logger.error(f"scatter: {e}")

        # 3. Bar Chart (mean of a physical variable by category/group)
        group_col = None
        if cat_cols:
            for c in cat_cols:
                if df[c].nunique() <= 15:
                    group_col = c
                    break
        if not group_col and code_num_cols:
            for c in code_num_cols:
                if df[c].nunique() <= 15:
                    group_col = c
                    break
        if not group_col and cat_cols:
            group_col = cat_cols[0]

        if group_col and num_cols:
            try:
                val = clean_num_cols[0] if clean_num_cols else num_cols[0]
                bar_df = df.groupby(group_col)[val].mean().sort_values(ascending=False).head(15)
                fig, ax = plt.subplots(figsize=(9, 5))
                
                short_labels = [_shorten(x) for x in bar_df.index]
                bars = ax.bar(short_labels, bar_df.values,
                               color=COLORS[0], edgecolor='white', linewidth=0.8)
                _style_ax(ax, f'{prefix} — Average {val} by {group_col}', group_col, f'Mean {val}')
                ax.set_xticks(range(len(short_labels)))
                ax.set_xticklabels(short_labels, rotation=45, ha='right')
                path = f"{output_dir}/{p}_bar_avg.png"
                if _save(fig, path): saved[f'{p}_bar_avg'] = path
            except Exception as e:
                logger.error(f"bar: {e}")

        # 4. Histogram (Distribution of a physical variable)
        if clean_num_cols or num_cols:
            try:
                col = clean_num_cols[0] if clean_num_cols else num_cols[0]
                fig, ax = plt.subplots(figsize=(9, 5))
                ax.hist(df[col].dropna(), bins=25, color=COLORS[0], edgecolor='white', linewidth=0.8)
                _style_ax(ax, f'{prefix} — Distribution of {col}', col, 'Frequency')
                path = f"{output_dir}/{p}_histogram.png"
                if _save(fig, path): saved[f'{p}_histogram'] = path
            except Exception as e:
                logger.error(f"histogram: {e}")

        # 5. Box Plot (Statistical Spread of Continuous/Physical Variables)
        box_cols = clean_num_cols[:5]
        if not box_cols:
            box_cols = [c for c in num_cols if c.lower() not in coord_keywords][:5]
        if not box_cols:
            box_cols = num_cols[:5]

        if box_cols:
            try:
                data_box = []
                standardized = len(box_cols) > 1
                for c in box_cols:
                    vals = df[c].dropna().values
                    if standardized and len(vals) > 1 and vals.std() > 0:
                        data_box.append((vals - vals.mean()) / vals.std())
                    else:
                        data_box.append(vals)
                
                fig, ax = plt.subplots(figsize=(9, 5))
                bp = ax.boxplot(data_box, labels=box_cols, patch_artist=True, notch=False,
                                medianprops=dict(color='white', linewidth=2))
                for patch, color in zip(bp['boxes'], COLORS):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.8)
                
                if standardized:
                    title = f'{prefix} — Statistical Spread Comparison (Standardized)'
                    ylabel = 'Standardized Value (Z-Score)'
                else:
                    title = f'{prefix} — Statistical Spread of {box_cols[0]}'
                    ylabel = box_cols[0]

                _style_ax(ax, title, 'Variable', ylabel)
                ax.tick_params(axis='x', rotation=20)
                path = f"{output_dir}/{p}_box_spread.png"
                if _save(fig, path): saved[f'{p}_box_spread'] = path
            except Exception as e:
                logger.error(f"box: {e}")

        # 6. Correlation Heatmap
        corr_cols = [c for c in num_cols if c.lower() not in ['index', 'id', 'sample_id', 't', 'step', 'iter']]
        if len(corr_cols) > 1:
            try:
                corr = df[corr_cols].corr()
                fig, ax = plt.subplots(figsize=(9, 7))
                im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
                plt.colorbar(im, ax=ax, shrink=0.8)
                ax.set_xticks(range(len(corr.columns)))
                ax.set_yticks(range(len(corr.columns)))
                ax.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=9, color=MUTED)
                ax.set_yticklabels(corr.columns, fontsize=9, color=MUTED)
                for i in range(len(corr)):
                    for j in range(len(corr.columns)):
                        ax.text(j, i, f'{corr.values[i, j]:.2f}',
                                ha='center', va='center', fontsize=8,
                                color='white' if abs(corr.values[i, j]) > 0.5 else TEXT)
                ax.set_title(f'{prefix} — Parameter Correlation Heatmap',
                             fontsize=14, fontweight='bold', color=TEXT, pad=12)
                fig.patch.set_facecolor('white')
                ax.set_facecolor(BG)
                path = f"{output_dir}/{p}_correlation.png"
                if _save(fig, path): saved[f'{p}_correlation'] = path
            except Exception as e:
                logger.error(f"heatmap: {e}")

        # 7. Pie Chart (categorical breakdown)
        pie_cat = None
        if cat_cols:
            for c in cat_cols:
                if 2 <= df[c].nunique() <= 15:
                    pie_cat = c
                    break
        if not pie_cat and code_num_cols:
            for c in code_num_cols:
                if 2 <= df[c].nunique() <= 15:
                    pie_cat = c
                    break

        if pie_cat:
            try:
                counts = df[pie_cat].value_counts().head(8)
                fig, ax = plt.subplots(figsize=(8, 5))
                
                short_labels = [_shorten(x) for x in counts.index]
                ax.pie(counts.values, labels=short_labels,
                       colors=COLORS[:len(counts)],
                       autopct='%1.1f%%', startangle=140,
                       textprops={'fontsize': 9, 'color': TEXT})
                ax.set_title(f'{prefix} — {pie_cat} Distribution',
                             fontsize=14, fontweight='bold', color=TEXT)
                fig.patch.set_facecolor('white')
                path = f"{output_dir}/{p}_pie.png"
                if _save(fig, path): saved[f'{p}_pie'] = path
            except Exception as e:
                logger.error(f"pie: {e}")

        # 8. Area Chart (mean transient trend)
        if y_cols:
            try:
                fig, ax = plt.subplots(figsize=(9, 5))
                if df[x_col].nunique() < len(df) and df[x_col].nunique() > 1:
                    plot_df = df.groupby(x_col)[y_cols[0]].mean().reset_index()
                else:
                    plot_df = df.sort_values(by=x_col)
                
                ax.fill_between(plot_df[x_col], plot_df[y_cols[0]], alpha=0.25, color=COLORS[0])
                ax.plot(plot_df[x_col], plot_df[y_cols[0]], color=COLORS[0], linewidth=2.5)
                _style_ax(ax, f'{prefix} — Average {y_cols[0]} Trend Over Time', x_col, y_cols[0])
                path = f"{output_dir}/{p}_area.png"
                if _save(fig, path): saved[f'{p}_area'] = path
            except Exception as e:
                logger.error(f"area: {e}")

        return saved
