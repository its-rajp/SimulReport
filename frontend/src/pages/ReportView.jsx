import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileText, Download, ArrowLeft, Calendar, Layers, Factory, CheckCircle, Loader } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000');

const ReportView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [selectedTab, setSelectedTab] = useState('');

  const getTabs = (rep) => {
    if (!rep?.dashboard_data) return [];
    const tabs = [];
    const dd = rep.dashboard_data;
    const srv = rep.service?.toUpperCase();
    
    if (srv === 'EFD') {
      if (dd.category_performance_img_id) tabs.push({ id: 'category_perf', label: 'Land Category Performance', key: 'category_performance_img_id' });
      if (dd.disposition_pareto_img_id) tabs.push({ id: 'disposition_pareto', label: 'Disposition Efficiency (Pareto)', key: 'disposition_pareto_img_id' });
      if (dd.commodity_donut_img_id) tabs.push({ id: 'commodity_donut', label: 'Commodity Composition', key: 'commodity_donut_img_id' });
    } else {
      if (dd.streamlines_img_id) tabs.push({ id: 'streamlines', label: 'Velocity Streamlines', key: 'streamlines_img_id' });
      if (dd.vector_field_img_id) tabs.push({ id: 'vector_field', label: 'Velocity Vectors (Quiver)', key: 'vector_field_img_id' });
      if (dd.convergence_img_id) tabs.push({ id: 'convergence', label: 'Convergence Residuals', key: 'convergence_img_id' });
      if (dd.velocity_profile_img_id) tabs.push({ id: 'velocity_profile', label: 'Velocity Profile (1D)', key: 'velocity_profile_img_id' });
      if (dd.mesh_img_id) tabs.push({ id: 'mesh', label: 'Computational Mesh Grid', key: 'mesh_img_id' });
    }
    
    return tabs;
  };

  useEffect(() => {
    fetch(`${API_BASE}/reports/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Report not found');
        return res.json();
      })
      .then(data => {
        setReport(data);
        const tabs = getTabs(data);
        if (tabs.length > 0) {
          setSelectedTab(tabs[0].id);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const handleDownload = async () => {
    if (!report?.download_url) return;
    setDownloading(true);
    try {
      const res = await fetch(`${API_BASE}${report.download_url}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = report.file_name || `${report.project_name}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Error downloading report. Please try again.');
    }
    setDownloading(false);
  };

  const getDashboardPlots = () => {
    if (!report?.dashboard_data) return null;
    const dd = report.dashboard_data;
    const srv = report.service?.toUpperCase();
    
    if (srv === 'CFD') {
      return {
        p1: dd.pressure_contour_img_id,
        p2: dd.velocity_magnitude_img_id,
        l1: 'Pressure Contour Map',
        l2: 'Velocity Magnitude Contour'
      };
    }
    if (srv === 'FEA') {
      return {
        p1: dd.stress_contour_img_id,
        p2: dd.displacement_img_id,
        l1: 'Von Mises Stress Contour',
        l2: 'Displacement / Deflection Plot'
      };
    }
    if (srv === 'DEM') {
      return {
        p1: dd.elevation_img_id,
        p2: dd.slope_img_id,
        l1: 'Terrain Elevation Map',
        l2: 'Slope Steepness Map'
      };
    }
    if (srv === 'EFD') {
      return {
        p1: dd.production_trend_img_id,
        p2: dd.commodity_comparison_img_id,
        l1: 'Total Production Volume Over Time',
        l2: 'Total Production by Commodity'
      };
    }
    return null;
  };

  const getStatsTable = () => {
    if (!report?.dashboard_data) return null;
    const dd = report.dashboard_data;
    const srv = report.service?.toUpperCase();
    
    if (srv === 'CFD') {
      return (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', background: 'white', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <thead>
            <tr style={{ background: '#ede9fe', borderBottom: '2px solid var(--border-color)' }}>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'left', fontWeight: '600', color: '#4c1d95' }}>Flow Metric</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Minimum Value</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Maximum Value</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Pressure (p)</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.min_pressure != null ? dd.min_pressure.toFixed(4) : 'N/A'}</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.max_pressure != null ? dd.max_pressure.toFixed(4) : 'N/A'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Velocity Magnitude (v_mag)</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>0.0000</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.max_velocity != null ? dd.max_velocity.toFixed(4) : 'N/A'}</td>
            </tr>
          </tbody>
        </table>
      );
    }
    if (srv === 'FEA') {
      return (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', background: 'white', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <thead>
            <tr style={{ background: '#ede9fe', borderBottom: '2px solid var(--border-color)' }}>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'left', fontWeight: '600', color: '#4c1d95' }}>Structural Metric</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Max Von Mises Stress</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.max_stress != null ? dd.max_stress.toFixed(4) : 'N/A'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Max Displacement / Deflection</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.max_displacement != null ? dd.max_displacement.toFixed(4) : 'N/A'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Min Factor of Safety (FOS)</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.min_fos != null ? dd.min_fos.toFixed(2) : 'N/A'}</td>
            </tr>
          </tbody>
        </table>
      );
    }
    if (srv === 'DEM') {
      return (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', background: 'white', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <thead>
            <tr style={{ background: '#ede9fe', borderBottom: '2px solid var(--border-color)' }}>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'left', fontWeight: '600', color: '#4c1d95' }}>Terrain Metric</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Elevation Range (z)</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>
                {dd.min_elevation != null ? dd.min_elevation.toFixed(2) : 'N/A'} to {dd.max_elevation != null ? dd.max_elevation.toFixed(2) : 'N/A'}
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Max Slope Gradient</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.max_slope != null ? `${dd.max_slope.toFixed(2)}°` : 'N/A'}</td>
            </tr>
          </tbody>
        </table>
      );
    }
    if (srv === 'EFD') {
      const formatProd = (val) => {
        if (val == null) return 'N/A';
        if (val >= 1e12) return `${(val/1e12).toFixed(1)} Trillion Units`;
        if (val >= 1e9) return `${(val/1e9).toFixed(1)} Billion Units`;
        if (val >= 1e6) return `${(val/1e6).toFixed(1)} Million Units`;
        return val.toLocaleString() + ' Units';
      };
      const statusBadge = (text, color) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color, fontWeight: '600', fontSize: '0.85rem' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, display: 'inline-block' }} />
          {text}
        </span>
      );
      return (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', background: 'white', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <thead>
            <tr style={{ background: '#ede9fe', borderBottom: '2px solid var(--border-color)' }}>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'left', fontWeight: '600', color: '#4c1d95' }}>KPI</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Value (Aggregated)</th>
              <th style={{ padding: '0.75rem 1.1rem', textAlign: 'center', fontWeight: '600', color: '#4c1d95' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Total Production Volume</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{formatProd(dd.total_production)}</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{statusBadge('Stable', '#10b981')}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Gas Commodity Share</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.gas_share_pct != null ? `${dd.gas_share_pct.toFixed(1)}%` : 'N/A'}</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{statusBadge('Major Driver', '#3b82f6')}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Onshore Contribution</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.onshore_pct != null ? `${dd.onshore_pct.toFixed(1)}%` : 'N/A'}</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{statusBadge('Primary Base', '#10b981')}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '0.75rem 1.1rem', fontWeight: '500' }}>Sales Efficiency</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{dd.sales_efficiency_pct != null ? `~${dd.sales_efficiency_pct.toFixed(0)}%` : 'N/A'}</td>
              <td style={{ padding: '0.75rem 1.1rem', textAlign: 'center' }}>{statusBadge('Healthy', '#10b981')}</td>
            </tr>
          </tbody>
        </table>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '6rem', gap: '1rem' }}>
        <Loader size={48} style={{ color: 'var(--primary-color)', animation: 'spin 1s linear infinite' }} />
        <p style={{ color: 'var(--text-muted)' }}>Loading report...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '6rem' }}>
        <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</p>
        <button className="btn btn-outline" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>
    );
  }

  const formattedDate = report.created_at
    ? new Date(report.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'N/A';

  const dashPlots = getDashboardPlots();
  const secondaryTabs = getTabs(report);

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '2rem 0' }}>
      {/* Back button */}
      <button className="btn btn-outline" style={{ marginBottom: '2rem' }} onClick={() => navigate('/dashboard')}>
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      {/* Report Header Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
            <div className="report-icon" style={{ width: '64px', height: '64px', flexShrink: 0 }}>
              <FileText size={32} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.75rem', fontWeight: '700', marginBottom: '0.5rem' }}>{report.project_name}</h1>
              <div className="report-meta" style={{ fontSize: '1rem', gap: '1.25rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Factory size={16} /> {report.industry}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Layers size={16} /> {report.service}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Calendar size={16} /> {formattedDate}
                </span>
              </div>
            </div>
          </div>
          <span className={`status-badge status-${report.status?.toLowerCase()}`} style={{ flexShrink: 0, fontSize: '0.875rem', padding: '0.4rem 1rem' }}>
            {report.status === 'Complete' ? <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><CheckCircle size={14} /> Complete</span> : `⚙️ ${report.status}`}
          </span>
        </div>
      </div>

      {report.status === 'Complete' ? (
        <>
          {/* Executive Dashboard Overview */}
          {report.dashboard_data && dashPlots && (
            <div className="card" style={{ marginBottom: '1.5rem', padding: '2rem' }}>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.25rem', color: 'var(--text-main)' }}>Executive Summary Dashboard</h2>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: '0.75rem', padding: '1rem', textAlign: 'center' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.75rem', color: 'var(--text-muted)' }}>{dashPlots.l1}</h3>
                  {dashPlots.p1 ? (
                    <img 
                      src={`${API_BASE}/download/${dashPlots.p1}`} 
                      alt={dashPlots.l1} 
                      style={{ width: '100%', borderRadius: '0.5rem', boxShadow: 'var(--shadow-sm)' }} 
                    />
                  ) : (
                    <div style={{ padding: '3rem', color: 'var(--text-muted)' }}>Contour plot not available</div>
                  )}
                </div>
                <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: '0.75rem', padding: '1rem', textAlign: 'center' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.75rem', color: 'var(--text-muted)' }}>{dashPlots.l2}</h3>
                  {dashPlots.p2 ? (
                    <img 
                      src={`${API_BASE}/download/${dashPlots.p2}`} 
                      alt={dashPlots.l2} 
                      style={{ width: '100%', borderRadius: '0.5rem', boxShadow: 'var(--shadow-sm)' }} 
                    />
                  ) : (
                    <div style={{ padding: '3rem', color: 'var(--text-muted)' }}>Contour plot not available</div>
                  )}
                </div>
              </div>

              {getStatsTable()}
            </div>
          )}

          {/* Supplemental Plots Explorer */}
          {report.dashboard_data && secondaryTabs.length > 0 && (
            <div className="card" style={{ marginBottom: '1.5rem', padding: '2rem' }}>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.25rem' }}>
                {report.service?.toUpperCase() === 'EFD' ? 'Supplemental Production Visualizations' : 'Supplemental Flow Visualizations'}
              </h2>
              
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', overflowX: 'auto', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                {secondaryTabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setSelectedTab(tab.id)}
                    style={{
                      padding: '0.5rem 1.25rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border-color)',
                      background: selectedTab === tab.id ? 'var(--primary-color)' : 'white',
                      color: selectedTab === tab.id ? 'white' : 'var(--text-muted)',
                      cursor: 'pointer',
                      fontWeight: '500',
                      fontSize: '0.875rem',
                      whiteSpace: 'nowrap',
                      transition: 'all 0.2s'
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              
              {(() => {
                const activeTabObj = secondaryTabs.find(t => t.id === selectedTab);
                const imgId = activeTabObj ? report.dashboard_data[activeTabObj.key] : null;
                
                if (imgId) {
                  return (
                    <div style={{ textAlign: 'center', background: '#f8fafc', padding: '1rem', borderRadius: '0.75rem', border: '1px solid var(--border-color)' }}>
                      <img
                        src={`${API_BASE}/download/${imgId}`}
                        alt={activeTabObj?.label}
                        style={{ maxWidth: '100%', maxHeight: '420px', borderRadius: '0.5rem', boxShadow: 'var(--shadow-md)' }}
                      />
                    </div>
                  );
                }
                return <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Select a tab to view secondary plots</div>;
              })()}
            </div>
          )}

          {/* Compact Download Section */}
          <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '0.5rem' }}>Your PDF Report is Ready</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
              Download the complete, publication-ready PDF report containing full executive summaries, AI interpretations, and all generated charts.
            </p>
            <button
              className="btn btn-primary"
              style={{ fontSize: '1rem', padding: '0.75rem 2rem' }}
              onClick={handleDownload}
              disabled={downloading}
            >
              <Download size={18} />
              {downloading ? 'Downloading...' : `Download PDF — ${report.file_name || 'report.pdf'}`}
            </button>
          </div>
        </>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          {report.status === 'Failed' ? (
            <>
              <div style={{ width: '80px', height: '80px', background: '#fef2f2', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                <span style={{ fontSize: '2rem' }}>❌</span>
              </div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.5rem' }}>Report Generation Failed</h2>
              <p style={{ color: 'var(--text-muted)' }}>
                An error occurred during report generation. Please try again or check the backend logs.
              </p>
            </>
          ) : (
            <>
              <div style={{ width: '80px', height: '80px', background: '#fffbeb', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                <Loader size={40} style={{ color: '#d97706', animation: 'spin 1s linear infinite' }} />
              </div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.5rem' }}>Report is Generating</h2>
              <p style={{ color: 'var(--text-muted)' }}>
                Your report is still being generated. Please check back in a moment.
              </p>
            </>
          )}
        </div>
      )}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default ReportView;
