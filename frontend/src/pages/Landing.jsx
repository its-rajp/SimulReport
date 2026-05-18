import React from 'react';
import { Link } from 'react-router-dom';
import { Zap, Activity, Layers, ShieldCheck, History, ArrowRight, BookOpen } from 'lucide-react';

const Landing = () => {
  return (
    <div>
      <section className="hero">
        <div className="badge">
          <Zap size={16} /> AI-POWERED ENGINEERING REPORTS
        </div>
        <h1 className="hero-title">
          Professional simulation reports, <span>generated in seconds</span>
        </h1>
        <p className="hero-subtitle">
          Upload your CFD, FEA, or DEM simulation data and receive a fully structured, standards-compliant engineering report — complete with methodology, results analysis, and recommendations.
        </p>
        <div className="hero-cta">
          <Link to="/generate" className="btn btn-primary">
            Generate a Report <ArrowRight size={18} />
          </Link>
          <Link to="/dashboard" className="btn btn-outline">
            View Past Reports
          </Link>
        </div>
      </section>

      <section className="glass-section">
        <h3 className="glass-title">Supported Industries</h3>
        <div className="pills-container">
          {["Oil & Gas", "Chemicals", "Pharmaceuticals", "Food & Beverages", "Metal & Mining", "Power Generation"].map((industry, i) => (
            <div key={i} className="pill">{industry}</div>
          ))}
        </div>
      </section>

      <section className="features-section">
        <h2 className="section-title">Everything your report needs</h2>
        <p className="section-subtitle">Built for engineering consulting firms that need to deliver high-quality technical documentation fast.</p>
        
        <div className="features-grid">
          <div className="card feature-card">
            <div className="feature-icon"><Zap size={24} /></div>
            <h3 className="feature-title">Instant Generation</h3>
            <p className="feature-desc">Upload your simulation data and get a fully structured technical report in under 60 seconds.</p>
          </div>
          <div className="card feature-card">
            <div className="feature-icon"><Layers size={24} /></div>
            <h3 className="feature-title">CFD • FEA • DEM • EFD</h3>
            <p className="feature-desc">Tailored report templates for every simulation discipline with discipline-specific terminology.</p>
          </div>
          <div className="card feature-card">
            <div className="feature-icon"><Activity size={24} /></div>
            <h3 className="feature-title">Structured Analysis</h3>
            <p className="feature-desc">Auto-populated results tables, parametric study summaries, and actionable recommendations.</p>
          </div>
          <div className="card feature-card">
            <div className="feature-icon"><BookOpen size={24} /></div>
            <h3 className="feature-title">Professional Sections</h3>
            <p className="feature-desc">Executive summary, methodology, results, conclusions, nomenclature, and full references.</p>
          </div>
          <div className="card feature-card">
            <div className="feature-icon"><ShieldCheck size={24} /></div>
            <h3 className="feature-title">Industry Compliance</h3>
            <p className="feature-desc">Reports reference appropriate standards: ASME, API, ISO, EN, NAFEMS, and more.</p>
          </div>
          <div className="card feature-card">
            <div className="feature-icon"><History size={24} /></div>
            <h3 className="feature-title">Saved History</h3>
            <p className="feature-desc">All generated reports are saved and accessible from your dashboard at any time.</p>
          </div>
        </div>
      </section>
      
      <section className="hero" style={{paddingTop: "2rem", paddingBottom: "6rem"}}>
          <h2 className="section-title">Ready to generate your first report?</h2>
          <p className="hero-subtitle" style={{marginBottom: "2rem"}}>No setup required. Upload your data files, configure your project, and get a professional report instantly.</p>
          <Link to="/generate" className="btn btn-primary">
            Get Started — It's Free <ArrowRight size={18} />
          </Link>
      </section>
    </div>
  );
};

export default Landing;
