import React from 'react';
import getApiUrl from '../config';

const LeadTable = ({ leads }) => {
  return (
    <div className="w-full overflow-x-auto bg-white/5 border border-white/10 rounded-3xl">
      <table className="w-full text-left border-collapse">
        <thead className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-white/40 border-b border-white/10">
          <tr>
            <th className="px-6 py-4">Potential Buyer</th>
            <th className="px-6 py-4">Location</th>
            <th className="px-6 py-4">Intent</th>
            <th className="px-6 py-4">Confidence</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {leads && leads.map((lead) => (
            <tr key={lead.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="px-6 py-4 font-bold text-white">{lead.buyer_name || "Verified Buyer"}</td>
              <td className="px-6 py-4 text-white/60 italic">{lead.location_raw}</td>
              <td className="px-6 py-4 text-white font-medium">{lead.intent_query}</td>
              <td className="px-6 py-4">
                <span className="bg-blue-600/20 text-blue-400 px-2 py-1 rounded text-[10px] font-black">
                  {(lead.intent_score * 100).toFixed(0)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeadTable;