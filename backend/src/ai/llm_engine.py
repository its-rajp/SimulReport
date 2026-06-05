from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from loguru import logger


class LLLEngine:
    def __init__(self):
        google_api_key = os.getenv("GOOGLE_API_KEY")

        if google_api_key:
            # Using gemini-flash-latest as it has active quota
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-flash-latest",
                google_api_key=google_api_key,
                temperature=0.3
            )
            logger.info("LLM Engine initialised with gemini-flash-latest")
        else:
            self.llm = None
            logger.warning("GOOGLE_API_KEY is missing. Returning placeholder text.")

    def _run_chain(self, prompt: PromptTemplate, context: dict, retries: int = 3) -> str:
        """Run prompt through Gemini using LCEL chain, with retry on quota errors."""
        chain = prompt | self.llm | StrOutputParser()

        for attempt in range(1, retries + 1):
            try:
                return chain.invoke(context)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Try to parse the suggested retry delay from the error message
                    wait = 60
                    try:
                        import re
                        match = re.search(r"retry in (\d+)", err_str, re.IGNORECASE)
                        if match:
                            wait = int(match.group(1)) + 5  # add 5s buffer
                    except Exception:
                        pass

                    if attempt < retries:
                        logger.warning(
                            f"Quota exceeded (attempt {attempt}/{retries}). "
                            f"Waiting {wait}s before retrying..."
                        )
                        time.sleep(wait)
                    else:
                        logger.error("All retry attempts exhausted due to quota limits.")
                        raise
                else:
                    raise

    def generate_report_content(self, service: str, industry: str, data_summary: str) -> str:
        """
        Generate the entire report structure in one shot based on the service type.
        This saves quota and ensures perfect flow across sections.
        """
        if not self.llm:
            return "[Placeholder Report. Please configure GOOGLE_API_KEY in backend/.env]"

        structures = {
            "CFD": """
1. General Numerical Method
Code & Strategy: Name of the numerical code (e.g., Star CCM+) and discretization scheme (FEM, FDM, FVM, etc.).
Physics Treatment: Treatment of fluid density (incompressible/compressible), pressure-velocity coupling (e.g., SIMPLE, PISO), and transient characteristics (steady/unsteady, time steps).
2. Grid System
Mesh Details: Grid generation software, coordinate system, grid type (tetrahedral, hexahedral, polyhedral, Cartesian), and structure (H/O/C/hybrid/unstructured).
Resolution: Motion handling method, total cell counts, surface cells, and non-dimensional first cell height (y+).
3. Numerical Schemes
Spatial Discretization: Discretization of convection term (centered, upwind, hybrid) and its order of accuracy.
Temporal Discretization: Temporal term discretization scheme (explicit/implicit, Runge-Kutta, Euler) and governing equations solved (mass, momentum, energy).
4. Boundary Conditions
Domain Boundaries: Boundary conditions specified for each domain (inlet velocity, outlet pressure, symmetry, slip/no-slip walls).
Wave Treatment (if applicable): Wave generation methods and wave absorption techniques (numerical beach, sponge layers, etc.).
5. Turbulence Modeling
Regime & Model: Flow regime (laminar, turbulent) and specific model type (URANS, k-epsilon, k-omega, Reynolds stress, DES, LES, DNS).
Treatments: Transition treatment and wall treatment (no-slip, wall function).
6. Free Surface Treatment
Interface Method: Free surface method (linearized, non-linear).
Tracking/Capturing: Free surface tracking versus capturing methods (MAC, VOF, level set).
7. Computations
Hardware: Computer details (processor type, count, memory) and system type (distributed, shared memory, PC cluster).
Execution: Parallel computing approach (MPI, OpenMP) and total wall clock simulation time.
8. Verification and Validation
Verification: Grid and time step convergence studies to ensure numerical precision.
Validation: Comparison of simulation results (e.g., drag force) to experimental data to confirm accuracy.
            """,
            "FEA": """
1. Executive Summary
Overview: Brief statement outlining the objective of the structural analysis.
Conclusion: Clear Pass/Fail determination based on safety factors.
2. Geometry & CAD Details
Description: Detailed breakdown of the component or assembly geometry.
Simplifications: Notes on minor features (fillets, chamfers) removed for meshing.
3. Material Properties
Material Selection: Exact material grades used and their mechanical properties.
Properties Defined: Young's Modulus, Poisson's Ratio, Yield Strength.
4. Meshing Strategy
Mesh Type: Element types used (Tetrahedral, Hexahedral, Shell).
Mesh Size & Quality: Element count, aspect ratio checks, and refinement zones.
5. Loads and Boundary Conditions
Loads: Magnitudes and vectors of applied forces, moments, or pressures.
Constraints: Fixed supports, frictionless surfaces, or remote displacements.
6. Stress & Deformation Analysis
Stress Analysis: Peak Von Mises and Principal stresses compared to yield.
Deformation: Maximum displacement and its impact on functionality.
7. Safety Factor Evaluation
FOS Mapping: Minimum Factor of Safety across the domain.
Critical Zones: Identification of areas prone to failure or fatigue.
8. Conclusion & Optimization Recommendations
Design Modifications: Proposed geometric changes (e.g., adding ribs, increasing thickness).
Weight Reduction: Opportunities to remove material in low-stress zones.
            """,
            "DEM": """
1. Executive Summary
Objectives: The primary purpose of the terrain and elevation study.
Data Origin: Details on how the Digital Elevation Model was acquired.
2. Data Origin & Resolution
Resolution: Spatial resolution, cell size, and vertical accuracy.
Coordinate System: Projection and datum details.
3. DEM Pre-processing & Quality
Internal Assessment: Artifact, sink, and peak removal processes.
Data Conditioning: Void filling and drainage enforcement techniques.
4. Slope & Aspect Analysis
Slope Analysis: Distribution of terrain steepness and gradients.
Aspect Analysis: Compass direction mapping of slopes.
5. Hydrological Modeling
Flow Accumulation: Identification of high water accumulation zones.
Stream Network: Delineation of potential channels and tributaries.
6. Flow Direction Mapping
Flow Vectors: Analysis of water movement across the surface.
Topographic Wetness: Index mapping for soil moisture potential.
7. Watershed Analysis
Catchment Areas: Mapping of drainage basin limits.
Outflow Points: Identification of primary pour points.
8. Conclusion & Next Steps
Risk Assessment: Areas prone to erosion or flooding.
Recommendations: Next steps for land use or infrastructure planning.
            """,
            "PROCESS MODELING": """
1. Executive Summary
Objectives: What specific chemical or industrial process is being modelled.
Key Outcomes: Summary of the principal results and yields.
2. Process Description & Scope
System Boundary: Clear definition of the process boundaries.
Inputs and Outputs: Feed streams, products, and utility requirements.
3. Model Setup & Thermodynamics
Software/Method: Modelling approach and equation of state used.
Thermodynamic Packages: Justification for the property method selected.
4. Unit Operations
Equipment List: Detailed description of reactors, columns, and exchangers.
Operating Conditions: Temperatures, pressures, and flow rates for key units.
5. Mass Balance Analysis
Component Balance: Detailed tracking of key components across streams.
Yield & Conversion: Overall process efficiency and product purity.
6. Energy Balance Analysis
Heating/Cooling Duties: Energy requirements for critical unit operations.
Net Efficiency: Overall thermal efficiency of the process.
7. Sensitivity & Optimization
Parametric Study: Effect of varying key process variables on the outcome.
Optimum Operating Point: Recommended set-points for maximum efficiency.
8. Conclusions & Recommendations
Process Performance: Key Performance Indicators (KPIs) vs targets.
Design Recommendations: Proposed changes to improve yield or reduce energy.
            """,
            "EFD": """
1. Executive Summary
Overview: Summarize the operational production and economic efficiency of the resource extraction operation for the full reporting period.
Key Metrics: Highlight Total Aggregated Production Volume, Period-over-Period Growth, Gas vs Oil commodity split, Onshore vs Offshore contribution, and Sales Efficiency (% of production reaching Sales-Royalty Due status).
2. Methodology & Mathematical Framework
Total Aggregated Volume: Explain the summation formula used: Total = Sigma(amount_i) for all records.
Period-over-Period (PoP) Growth: Define and apply: Growth = (Amount_current - Amount_previous) / Amount_previous x 100.
Resource Composition: Show commodity share calculation: Share = (Amount_commodity / Total) x 100.
Moving Average: Explain the 12-month SMA used to smooth production trend volatility.
Cumulative Frequency: Describe the Pareto ranking formula for disposition analysis.
3. Performance Insights
Production Trends: Analyze the temporal trend line chart. Identify periods of growth, decline, and seasonal cycles across the dataset's date range.
Resource & Regional Composition: Analyze the stacked bar chart of Land Category (Onshore vs Offshore) over time. Discuss which category dominates and how the mix has shifted.
Disposition Efficiency (Pareto Analysis): Analyze the Pareto chart. Explain which Disposition Descriptions (e.g., Sales-Royalty Due) account for the majority of volume, and which represent operational losses (Flared, Vented, Injected).
4. Key Performance Indicators (KPI) Table
Present a structured KPI summary table with these rows: Total Production Volume (with status: Stable/Growing/Declining), Gas Commodity Share (% with status: Major Driver), Onshore Contribution (% with status: Primary Base), Sales Efficiency (% with status: Healthy/Warning).
Include interpretation of each KPI's significance to stakeholders.
5. Strategic Recommendations
Prioritize Onshore Assets: Explain why onshore maintenance is critical if it is the primary production base.
Loss Mitigation: Recommend root-cause analysis on Flared/Vented gas dispositions. Quantify the potential revenue recovery from reducing flaring by 1%.
Reporting Cadence: Recommend monthly automated EFD reporting using the Sales Efficiency metric as the primary health indicator.
6. Appendix: Data Quality & Methodology Notes
Data Source: Describe the OGORB dataset — columns, date range, and granularity.
Cleaning Steps: Note any data transformations (date parsing, numeric coercion, NaN handling).
Known Limitations: Document any assumptions or gaps in the analysis.
7. Commodity Deep-Dive
Gas (Mcf) Analysis: Detailed production trends, regional distribution, and disposition breakdown for natural gas.
Oil (bbl) Analysis: Detailed production trends, regional distribution, and disposition breakdown for crude oil.
Comparative Analysis: Side-by-side comparison of Gas vs Oil across all dimensions.
8. Conclusion & Future Outlook
Summary of Findings: Consolidate the key takeaways from all sections.
Forecasted Trends: Based on historical patterns, project likely production trajectories.
Recommended Next Steps: Actionable items for the next reporting period.
            """
        }

        # Fallback structure
        fallback_structure = """
1. Executive Summary
Objectives: A clear statement of the project goals.
Key Findings: The most critical insights from the data.
2. Objectives and Scope
Scope: The boundaries of the analysis.
Data Sources: A brief description of the datasets used.
3. Methodology
Approach: The analytical methods and algorithms applied.
Assumptions: Any constraints or assumptions made during analysis.
4. Data Processing
Cleaning: Steps taken to clean and prepare the data.
Transformations: Any feature engineering or normalization performed.
5. Primary Analysis
Core Trends: The main trends discovered in the dataset.
Correlations: Significant relationships between variables.
6. Secondary Insights
Anomalies: Outliers or unexpected patterns in the data.
Sub-group Analysis: Findings specific to certain categories or clusters.
7. Results Validation
Robustness: How the findings were validated or verified.
Limitations: Potential weaknesses in the analysis.
8. Conclusion
Final Takeaways: A summary of the most important conclusions.
Recommendations: Actionable next steps based on the findings.
        """
        
        structure = structures.get(service.upper(), fallback_structure)

        prompt = PromptTemplate(
            input_variables=["industry", "service", "data_summary", "structure", "word_count_instruction"],
            template="""You are a senior {service} expert writing a formal, well-structured engineering report for the {industry} industry.

The following is a complete data profile of the uploaded CSV file(s). This is the ONLY source of truth. Every section of your report MUST directly reference the actual column names, values, statistics, and findings from this data. Do NOT write generic content.

=== UPLOADED DATA PROFILE ===
{data_summary}
=== END DATA PROFILE ===

Write a concise, precisely structured technical report. Follow this exact 8-section structure:
{structure}

FORMATTING RULES (VERY IMPORTANT — follow these exactly):
1. Use `#` for main section headings (e.g., `# 1. Introduction & Objectives`)
2. Use `##` for sub-section headings within each section (e.g., `## Background`, `## Key Objectives`)
3. Use `###` for detailed sub-topics under sub-sections where applicable
4. Use bullet points (`* `) for listing key findings, parameters, or data points
5. Keep body paragraphs SHORT — maximum 3-4 sentences each
6. After each paragraph, leave a blank line for spacing

CONTENT RULES:
1. Reference EXACT column names from the data in every section.
2. Cite SPECIFIC numerical values (means, ranges, peaks, anomalies) found in the data.
3. Mention the actual file name(s) in the introduction.
4. Use proper Unicode mathematical symbols for equations and variables (e.g., use ∂ instead of d, ρ instead of rho, τ instead of tau, α, β, etc.). Do NOT spell them out. Do NOT use LaTeX $ signs, just output standard Unicode text.
5. Do NOT write introductory filler like "Here is the report". Start directly with the first section heading.
6. Write {word_count_instruction} words per section. Be precise and data-driven — every sentence must reference specific data.
7. You MUST generate exactly all 8 sections listed in the structure, no more, no less.
8. Each section MUST have at least 2 sub-headings (##) and use bullet points for key data.

EXAMPLE STRUCTURE FOR A SECTION:
```
# 1. Introduction & Objectives

## Background
Brief 2-3 sentence overview referencing the file name and key columns.

## Key Objectives
* Analyze the distribution of [Column Name] (mean: X, range: Y-Z)
* Evaluate correlation between [Column A] and [Column B]
* Identify anomalies in [Column C] across the dataset
```

Output ONLY the Markdown report text.
"""
        )

        # EFD gets longer sections for 10-15 page PDFs; other services stay concise
        word_count = "200-300" if service.upper() == "EFD" else "120-150"

        try:
            result = self._run_chain(prompt, {
                "industry": industry,
                "service": service,
                "data_summary": data_summary,
                "structure": structure,
                "word_count_instruction": word_count
            })
            logger.info(f"Successfully generated full report content for {service}.")
            return result
        except Exception as e:
            logger.error(f"Error generating report content: {e}")
            return f"# Error\n\nCould not generate content: {str(e)}"
