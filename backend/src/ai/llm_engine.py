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
1. Introduction & Objectives
Background: A brief overview of the fluid problem being studied.
Objectives: Clear, quantifiable goals of the simulation.
2. Physical Model & Geometry
Geometry: Description of the computational model.
Assumptions: Simplifications made.
3. Methodology & Setup
Mesh Details: Mesh type, element count, strategy.
Governing Equations: Fluid laws and principles used.
Boundary Conditions: Defined limits, inlet, outlet, walls.
Turbulence Model: The specific turbulence model chosen.
4. Results & Discussion
Visualizations: Explanation of the plots generated.
Data extraction: Quantitative engineering results.
5. Validation & Conclusion
Grid Independence Study: Mesh refinement analysis.
Validation: Comparison against theory/experiments.
Design Recommendations: Final conclusions.
            """,
            "FEA": """
1. Executive Summary
Overview: Brief statement outlining the objective.
Conclusion: Clear Pass/Fail determination.
2. Geometry & CAD Details
Description: Details of the component/assembly.
Simplifications: Notes on minor features removed.
3. Material Properties
Material Selection: Exact material grades used.
Properties Defined: Young's Modulus, Poisson's Ratio, etc.
4. Meshing
Mesh Type: Elements used (1D/2D/3D).
Mesh Size & Quality: Element count and refinement.
5. Loads and Boundary Conditions (BCs)
Loads: Magnitudes and directions of forces/pressures.
Constraints: How the model is fixed/supported.
6. Results and Evaluation
Stress Analysis: Explanation of Von Mises or principal stresses.
Deformation: Displacement evaluation.
Safety Factor: Factor of Safety (FOS) calculation.
7. Recommendations
Design Modifications: Proposed changes.
Optimization: Recommendations to reduce weight.
            """,
            "DEM": """
1. Executive Summary
Objectives: The purpose of the study.
Data Origin: Details on how DEM was acquired.
Resolution: Cell size and accuracy.
2. DEM Pre-processing & Quality Assessment
Internal Assessment: Artifact/sink removal.
External Assessment: Ground truth comparison.
Data Conditioning: Void filling and drainage enforcement.
3. Core Terrain Analyses
Slope Analysis: Steepness of terrain.
Aspect Analysis: Compass direction mapping.
Contour Generation: Lines of equal elevation.
4. Hydrological Modeling
Flow Direction and Accumulation: Water movement.
Stream Network Delineation: Channels and catchments.
Watershed Boundary Mapping: Drainage basin limits.
            """,
            "EFD": """
1. Executive Summary
Overview: Brief overview of reporting period.
Key Metrics: Highlights of total sales, taxes collected, compliance rates.
2. Business & EFD Machine Profile
Company Details: Name, TIN, location.
Machine Details: Serial numbers and fiscalization status.
3. Transaction Data & Sales Analysis
Gross vs. Net Sales: Total revenue vs non-taxable.
Transaction Breakdown: Volume by hour/day/shift.
Z-Report Summary: Daily totals.
4. Tax Compliance & EFDMS Data
EFDMS Reconciliation: Matching records with tax server.
VAT Liability: Breakdown of standard VAT rates.
5. Exceptions & Anomaly Reporting
Voids and Cancellations: Canceled/modified transactions.
System Errors/Downtime: Machine malfunction/offline periods.
Offline Transactions: Sales made without server connection.
6. Recommendations & Action Plan
Operational Fixes: Steps to resolve hardware/network issues.
Compliance Improvements: Corrective measures.
            """
        }

        # Fallback structure
        fallback_structure = """
1. Executive Summary
Objectives and Key Findings.
2. Methodology
Approach and Data Processing.
3. Results
Data Insights and Visualizations.
4. Conclusion
Final Takeaways.
        """
        
        structure = structures.get(service.upper(), fallback_structure)

        prompt = PromptTemplate(
            input_variables=["industry", "service", "data_summary", "structure"],
            template="""You are a senior {service} expert consulting for the {industry} industry.

You must write a comprehensive, highly technical engineering/financial report based on the data summary provided.

### Data Summary:
{data_summary}

### Required Report Structure:
You MUST follow this exact structure and formatting. Use Markdown `#` for main sections and `##` or `###` for sub-sections.
{structure}

### Formatting Rules for Mathematical Equations:
CRITICAL: Do NOT use LaTeX or TeX formatting (`$$`, `\frac`, `\partial`, `\nabla`, `\otimes`, etc.). ReportLab does not support raw LaTeX.
Instead, write all mathematical formulas, governing equations, and symbols using plain text, standard Unicode symbols, or simple notation (e.g., write "∂ρ/∂t + ∇·(ρu) = 0" or "F = m * a" or "k-epsilon"). You may use standard HTML tags like `<sub>` or `<sup>` if needed.

Ensure perfect grammar, authoritative tone, and professional flow. Use specific engineering/financial terminology appropriate for {service}. Do NOT write introductory filler like "Here is the report". Output ONLY the report text in Markdown.
"""
        )

        try:
            result = self._run_chain(prompt, {
                "industry": industry,
                "service": service,
                "data_summary": data_summary,
                "structure": structure
            })
            logger.info(f"Successfully generated full report content for {service}.")
            return result
        except Exception as e:
            logger.error(f"Error generating report content: {e}")
            return f"# Error\n\nCould not generate content: {str(e)}"
