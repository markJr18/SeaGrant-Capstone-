import React, { useState, useEffect } from 'react';
import './App.css';

interface Report {
  id: number;
  title: string;
  summary: string;
  fullUrl: string;
  date: string;
  type: string;
  topics: string;
}

const SeaGrantApp: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const keywords = ['Wetland', 'Coastal', 'Resilience', 'Erosion', 'Water Quality', 'Oyster', 'Flooding', 'Stormwater'];

  const fetchReports = async (keyword: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:3001/api/reports?keyword=${encodeURIComponent(keyword)}`);
      if (!response.ok) throw new Error('Failed to fetch reports');
      const data = await response.json();
      setReports(data);
    } catch (err) {
      console.error(err);
      setError('Could not load real-time reports. Please ensure the scraper server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeywordClick = (keyword: string) => {
    setSelectedKeyword(keyword);
    fetchReports(keyword);
  };

  return (
    <div className="app-container">
      <header>
        <h1>SeaGrant Wetland Preservation</h1>
        <p>South Carolina Coastal Wetlands Information Portal</p>
      </header>

      <main>
        <section className="search-section">
          <div className="search-input-wrapper">
            <input
              type="text"
              placeholder="Search documents and reports..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="keyword-chips">
            {keywords
              .filter(k => k.toLowerCase().includes(searchTerm.toLowerCase()))
              .map(keyword => (
                <button
                  key={keyword}
                  onClick={() => handleKeywordClick(keyword)}
                  className={selectedKeyword === keyword ? 'active' : ''}
                >
                  {keyword}
                </button>
              ))}
          </div>
        </section>

        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Scraping real-time SC Coastal documents...</p>
          </div>
        )}

        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        {!loading && selectedKeyword && reports.length === 0 && (
          <div className="no-results">
            <p>No documents found for "{selectedKeyword}". Try another keyword.</p>
          </div>
        )}

        {!loading && reports.length > 0 && (
          <section className="reports-section">
            <div className="section-header">
              <h2>Real-Time Documents for: {selectedKeyword}</h2>
              <span className="count-badge">{reports.length} found</span>
            </div>
            <div className="report-list">
              {reports.map(report => (
                <div key={report.id} className="report-card">
                  <div className="card-meta">
                    <span className="report-type">{report.type}</span>
                    <span className="report-date">{report.date}</span>
                  </div>
                  <h3>{report.title}</h3>
                  <p className="report-summary">{report.summary}</p>
                  <div className="report-topics">
                    {report.topics.split(',').map(topic => (
                      <span key={topic} className="topic-tag">{topic.trim()}</span>
                    ))}
                  </div>
                  <a href={report.fullUrl} target="_blank" rel="noopener noreferrer" className="view-link">
                    View Full Report
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                  </a>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default SeaGrantApp;

