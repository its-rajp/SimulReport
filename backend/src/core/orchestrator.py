from src.core.file_parser import FileParser
from src.ai.llm_engine import LLLEngine
from src.viz.graph_generator import GraphGenerator
from src.export.pdf_builder import PDFBuilder
from models import create_report, update_report_status
from pathlib import Path
from loguru import logger
import traceback
import tempfile
import shutil
import pandas as pd
from src.core.firebase_storage import CloudStorage


class ReportOrchestrator:
    def __init__(self):
        self.llm = LLLEngine()
        self.file_parser = FileParser()

    def generate_full_report(self, file_paths: list, params: dict):
        """Main orchestrator workflow for synchronous requests"""
        logger.info("Starting synchronous report generation...")

        report_id = create_report(
            project_name=params.get("project_name", "Untitled"),
            industry=params.get("industry", ""),
            service=params.get("service", ""),
            status="Generating",
        )

        return self._run_generation_pipeline(report_id, file_paths, params)

    def generate_full_report_with_id(self, report_id: str, file_paths: list, params: dict):
        """Workflow for Celery background tasks (DB record already exists)"""
        logger.info(f"Starting async report generation for task {report_id}...")
        update_report_status(report_id, "Generating")
        return self._run_generation_pipeline(report_id, file_paths, params)

    def _run_generation_pipeline(self, report_id: str, file_ids: list, params: dict):
        """Core pipeline logic — downloads files from Firebase Storage, runs LLM, builds PDF,
        uploads result back to Firebase Storage, and updates the report status in Firestore."""

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Download files from Firebase Storage to a temp directory
            temp_paths = []
            for file_id in file_ids:
                # file_id here is the UUID_filename string we saved in CloudStorage
                file_bytes = CloudStorage.get_file(file_id)
                if file_bytes:
                    # extract the original filename from the stored file_id
                    original_filename = file_id.split('_', 1)[-1] if '_' in file_id else file_id
                    temp_path = Path(temp_dir) / original_filename
                    with open(temp_path, "wb") as f:
                        f.write(file_bytes)
                    temp_paths.append(str(temp_path))

            # 2. Parse all files
            all_data = {}
            for file_path in temp_paths:
                file_type = Path(file_path).suffix[1:]
                all_data[file_path] = self.file_parser.parse_file(file_path, file_type)

            # 3. Build a rich data profile for the LLM context
            data_profile_parts = []
            for path, data in all_data.items():
                fname = Path(path).name
                if "data" not in data or data["data"].empty:
                    data_profile_parts.append(f"File: {fname}\n  (No tabular data found)")
                    continue

                df = data["data"]
                profile_lines = [f"=== File: {fname} ==="]
                profile_lines.append(f"Rows: {len(df)}  |  Columns: {len(df.columns)}")
                profile_lines.append(f"Column names: {list(df.columns)}")

                sample = df.head(5).to_string(index=False, max_cols=20)
                profile_lines.append(f"\nFirst 5 rows:\n{sample}")

                num_df = df.select_dtypes(include=["number"])
                if not num_df.empty:
                    stats = num_df.describe().loc[["mean", "min", "max", "std"]].round(3)
                    profile_lines.append(f"\nNumerical column statistics:\n{stats.to_string()}")

                cat_df = df.select_dtypes(exclude=["number"])
                if not cat_df.empty:
                    cat_lines = ["\nCategorical/text columns (top values):"]
                    for col in cat_df.columns:
                        top = df[col].value_counts().head(5)
                        cat_lines.append(f"  {col}: {list(top.index)}")
                    profile_lines.append("\n".join(cat_lines))

                data_profile_parts.append("\n".join(profile_lines))

            data_summary = "\n\n".join(data_profile_parts) if data_profile_parts else "No data found."
            data_summary = data_summary[:4000]

            logger.info(f"Data profile built ({len(data_summary)} chars). Sending to LLM...")

            # 4. Generate report content via LLM
            service = params.get("service", "Analysis")
            industry = params.get("industry", "General")

            report_content = {
                "full_text": self.llm.generate_report_content(
                    service=service,
                    industry=industry,
                    data_summary=data_summary,
                )
            }

            # 5. Generate visualizations
            viz_files = {}
            viz_dir = Path(temp_dir) / "viz"
            viz_dir.mkdir(parents=True, exist_ok=True)
            main_df = None
            for file_path, data in all_data.items():
                if "data" in data and not data["data"].empty:
                    main_df = data["data"]
                    viz_files.update(
                        GraphGenerator.create_service_visualizations(
                            data["data"], str(viz_dir), service
                        )
                    )

            # Upload visualization images to Firebase Storage and map their IDs
            import os
            import numpy as np
            gridfs_image_ids = {}
            for name, path in viz_files.items():
                if os.path.exists(path):
                    try:
                        with open(path, "rb") as img_f:
                            img_bytes = img_f.read()
                        gridfs_id = CloudStorage.save_file(img_bytes, os.path.basename(path))
                        gridfs_image_ids[name] = gridfs_id
                    except Exception as e:
                        logger.error(f"Failed to upload visualization {name} to Firebase Storage: {e}")

            # Compute statistics and populate dashboard_data
            dashboard_data = {}
            stats_dict = {}
            
            if main_df is not None:
                def get_col_from_df(keywords):
                    for c in main_df.columns:
                        if c.lower() in [k.lower() for k in keywords]:
                            return c
                    return next((c for c in main_df.columns if any(k in c.lower() for k in keywords)), None)

                srv_upper = service.upper()
                if srv_upper == "CFD":
                    p_col = get_col_from_df(["p", "press", "pressure"])
                    u_col = get_col_from_df(["u", "vel_x", "vx"])
                    v_col = get_col_from_df(["v", "vel_y", "vy"])
                    
                    max_p = float(main_df[p_col].max()) if p_col else None
                    min_p = float(main_df[p_col].min()) if p_col else None
                    max_v = None
                    if u_col and v_col:
                        vel_mag = np.sqrt(main_df[u_col]**2 + main_df[v_col]**2)
                        max_v = float(vel_mag.max())
                    elif u_col:
                        max_v = float(main_df[u_col].abs().max())
                    
                    stats_dict = {
                        "max_pressure": max_p,
                        "min_pressure": min_p,
                        "max_velocity": max_v,
                    }
                    dashboard_data = {
                        **stats_dict,
                        "pressure_contour_img_id": gridfs_image_ids.get("cfd_scalar_pressure"),
                        "velocity_magnitude_img_id": gridfs_image_ids.get("cfd_scalar_velocity"),
                        "streamlines_img_id": gridfs_image_ids.get("cfd_streamlines"),
                        "vector_field_img_id": gridfs_image_ids.get("cfd_vector_velocity"),
                        "convergence_img_id": gridfs_image_ids.get("cfd_convergence"),
                        "velocity_profile_img_id": gridfs_image_ids.get("cfd_velocity_profile"),
                        "mesh_img_id": gridfs_image_ids.get("cfd_mesh_display"),
                    }
                elif srv_upper == "FEA":
                    stress_col = get_col_from_df(["stress", "mises"])
                    disp_col = get_col_from_df(["disp", "deflect"])
                    fos_col = get_col_from_df(["fos", "safety"])
                    
                    max_stress = float(main_df[stress_col].max()) if stress_col else None
                    max_disp = float(main_df[disp_col].max()) if disp_col else None
                    min_fos = float(main_df[fos_col].min()) if fos_col else None
                    
                    stats_dict = {
                        "max_stress": max_stress,
                        "max_displacement": max_disp,
                        "min_fos": min_fos,
                    }
                    dashboard_data = {
                        **stats_dict,
                        "stress_contour_img_id": gridfs_image_ids.get("fea_stress"),
                        "displacement_img_id": gridfs_image_ids.get("fea_displacement"),
                    }
                elif srv_upper == "DEM":
                    elev_col = get_col_from_df(["elev", "height", "z"])
                    slope_col = get_col_from_df(["slope", "grad"])
                    
                    max_elev = float(main_df[elev_col].max()) if elev_col else None
                    min_elev = float(main_df[elev_col].min()) if elev_col else None
                    max_slope = float(main_df[slope_col].max()) if slope_col else None
                    
                    stats_dict = {
                        "max_elevation": max_elev,
                        "min_elevation": min_elev,
                        "max_slope": max_slope,
                    }
                    dashboard_data = {
                        **stats_dict,
                        "elevation_img_id": gridfs_image_ids.get("dem_elevation"),
                        "slope_img_id": gridfs_image_ids.get("dem_slope"),
                    }
                elif srv_upper == "EFD":
                    amt_col = get_col_from_df(["amount", "sale", "revenue"])
                    date_col = get_col_from_df(["date", "time"])
                    comm_col = get_col_from_df(["commodity"])
                    cat_col = None
                    for c in main_df.columns:
                        if 'land' in c.lower() and 'cat' in c.lower():
                            cat_col = c
                            break
                    if not cat_col:
                        cat_col = get_col_from_df(["category"])
                    disp_col = None
                    for c in main_df.columns:
                        if 'disposition' in c.lower() and 'desc' in c.lower():
                            disp_col = c
                            break
                    if not disp_col:
                        disp_col = get_col_from_df(["disposition"])

                    # 1. Total Production Volume
                    total_production = float(main_df[amt_col].sum()) if amt_col else None

                    # 2. Period-over-Period Growth %
                    pop_growth_pct = None
                    if amt_col and date_col:
                        try:
                            temp_df = main_df.copy()
                            temp_df['_dt'] = pd.to_datetime(temp_df[date_col], errors='coerce')
                            temp_df = temp_df.dropna(subset=['_dt'])
                            temp_df['_year'] = temp_df['_dt'].dt.year
                            yearly = temp_df.groupby('_year')[amt_col].sum()
                            if len(yearly) >= 2:
                                last_yr = yearly.iloc[-1]
                                prev_yr = yearly.iloc[-2]
                                if prev_yr != 0:
                                    pop_growth_pct = float((last_yr - prev_yr) / prev_yr * 100)
                        except Exception:
                            pass

                    # 3. Gas Commodity Share %
                    gas_share_pct = None
                    if comm_col and amt_col:
                        try:
                            comm_totals = main_df.groupby(comm_col)[amt_col].sum()
                            total_amt = comm_totals.sum()
                            gas_rows = comm_totals[comm_totals.index.str.lower().str.contains('gas')]
                            if total_amt > 0 and len(gas_rows) > 0:
                                gas_share_pct = float(gas_rows.sum() / total_amt * 100)
                        except Exception:
                            pass

                    # 4. Onshore Contribution %
                    onshore_pct = None
                    if cat_col and amt_col:
                        try:
                            cat_totals = main_df.groupby(cat_col)[amt_col].sum()
                            total_amt = cat_totals.sum()
                            onshore_rows = cat_totals[cat_totals.index.str.lower().str.contains('onshore')]
                            if total_amt > 0 and len(onshore_rows) > 0:
                                onshore_pct = float(onshore_rows.sum() / total_amt * 100)
                        except Exception:
                            pass

                    # 5. Sales Efficiency %
                    sales_efficiency_pct = None
                    if disp_col and amt_col:
                        try:
                            disp_totals = main_df.groupby(disp_col)[amt_col].sum()
                            total_amt = disp_totals.sum()
                            sales_rows = disp_totals[disp_totals.index.str.lower().str.contains('sale')]
                            if total_amt > 0 and len(sales_rows) > 0:
                                sales_efficiency_pct = float(sales_rows.sum() / total_amt * 100)
                        except Exception:
                            pass

                    # 6. Top Category & Top Disposition
                    top_category = None
                    if cat_col and amt_col:
                        try:
                            top_category = str(main_df.groupby(cat_col)[amt_col].sum().idxmax())
                        except Exception:
                            pass

                    top_disposition = None
                    if disp_col and amt_col:
                        try:
                            top_disposition = str(main_df.groupby(disp_col)[amt_col].sum().idxmax())
                        except Exception:
                            pass

                    # 7. Date Range
                    date_range_str = None
                    if date_col:
                        try:
                            dt_series = pd.to_datetime(main_df[date_col], errors='coerce').dropna()
                            if not dt_series.empty:
                                date_range_str = f"{dt_series.min().strftime('%Y-%m')} to {dt_series.max().strftime('%Y-%m')}"
                        except Exception:
                            pass

                    stats_dict = {
                        "total_production": total_production,
                        "pop_growth_pct": pop_growth_pct,
                        "gas_share_pct": gas_share_pct,
                        "onshore_pct": onshore_pct,
                        "sales_efficiency_pct": sales_efficiency_pct,
                        "top_category": top_category,
                        "top_disposition": top_disposition,
                        "date_range": date_range_str,
                    }
                    dashboard_data = {
                        **stats_dict,
                        "production_trend_img_id": gridfs_image_ids.get("efd_production_trend"),
                        "commodity_comparison_img_id": gridfs_image_ids.get("efd_commodity_comparison"),
                        "category_performance_img_id": gridfs_image_ids.get("efd_category_performance"),
                        "disposition_pareto_img_id": gridfs_image_ids.get("efd_disposition_pareto"),
                        "commodity_donut_img_id": gridfs_image_ids.get("efd_commodity_donut"),
                    }

            # Pass calculated stats in params to the PDF builder
            params["dashboard_stats"] = stats_dict

            # 6. Build final PDF
            pdf_builder = PDFBuilder()
            report_path = pdf_builder.build_report(
                report_content, viz_files, params, output_dir=Path(temp_dir)
            )

            # 7. Upload final PDF to Firebase Storage
            with open(report_path, "rb") as f:
                pdf_bytes = f.read()
            final_pdf_id = CloudStorage.save_file(pdf_bytes, Path(report_path).name)

            logger.info(f"Report saved to Firebase Storage with ID: {final_pdf_id}")

            # 8. Update report status in Firestore
            update_report_status(report_id, "Complete", file_path=final_pdf_id, dashboard_data=dashboard_data)

            return final_pdf_id

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            logger.error(traceback.format_exc())
            update_report_status(report_id, "Failed")
            raise e
        finally:
            # Always clean up temp files to save disk space
            shutil.rmtree(temp_dir, ignore_errors=True)
