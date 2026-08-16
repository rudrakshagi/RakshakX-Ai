import React, { useState } from 'react';
import { VulnerabilityFinding, SeverityLevel } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';
import { Search, Filter, Terminal, CheckCircle2, ShieldAlert, ArrowUpRight } from 'lucide-react';

interface FindingsLedgerProps {
  findings: VulnerabilityFinding[];
  onSelectFinding: (finding: VulnerabilityFinding) => void;
}

export const FindingsLedger: React.FC<FindingsLedgerProps> = ({
  findings,
  onSelectFinding,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const filteredFindings = findings.filter((f) => {
    const matchesSearch =
      f.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.endpoint.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.cwe_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.category.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSeverity =
      severityFilter === 'all' || f.severity === severityFilter;

    return matchesSearch && matchesSeverity;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Search & Filter Bar */}
      <div className="p-4 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col sm:flex-row gap-4 items-center justify-between">
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search findings, endpoints, CWE..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500"
          />
        </div>

        {/* Severity Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                severityFilter === sev
                  ? 'bg-slate-900 text-white dark:bg-brand-600 dark:text-white shadow-xs'
                  : 'bg-slate-50 dark:bg-[#121B2D] text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-slate-300'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Findings Table */}
      <div className="rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
            Confirmed Findings Ledger ({filteredFindings.length})
          </div>
          <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
            All findings verified with executable PoCs
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 dark:bg-[#121B2D] text-slate-400 font-bold uppercase tracking-wider text-[10px] border-b border-slate-100 dark:border-slate-800">
                <th className="p-4" style={{ width: '120px' }}>Severity</th>
                <th className="p-4">Vulnerability Title</th>
                <th className="p-4">Category & CWE</th>
                <th className="p-4">Impacted Endpoint</th>
                <th className="p-4" style={{ width: '100px' }}>Evidence</th>
                <th className="p-4 text-right" style={{ width: '110px' }}>Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-medium text-slate-700 dark:text-slate-300">
              {filteredFindings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    No findings match the selected filters.
                  </td>
                </tr>
              ) : (
                filteredFindings.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => onSelectFinding(f)}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="p-4">
                      <SeverityBadge severity={f.severity} score={f.cvss_score} />
                    </td>
                    <td className="p-4">
                      <div className="font-bold text-slate-900 dark:text-slate-100 text-xs sm:text-sm">
                        {f.title}
                      </div>
                      <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                        {f.description}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="font-mono text-slate-600 dark:text-slate-400">{f.cwe_id}</div>
                      <div className="text-[10px] text-slate-400">{f.category}</div>
                    </td>
                    <td className="p-4">
                      <span className="font-mono text-slate-700 dark:text-sky-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-[11px] border border-slate-200 dark:border-slate-700">
                        {f.endpoint}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Verified
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectFinding(f);
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
