import React from 'react';
import { Brain, Code, Cloud, Database, PenTool, Briefcase, Search, RefreshCw, Upload } from 'lucide-react';

const SkillBadge = ({ skill, icon: Icon, colorClass }) => (
  <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium ${colorClass} bg-opacity-10 border border-opacity-20 mr-2 mb-2 max-w-full overflow-hidden`} title={skill}>
    {Icon && <Icon className="w-3 h-3 mr-1 flex-shrink-0" />}
    <span className="truncate">{skill}</span>
  </span>
);

const ResumeInsights = ({ data, onReplace, onRestart }) => {
  if (!data) return null;

  const { skills, roles, queries, filename, uploaded_at } = data;

  const hasSkills = skills && Object.values(skills).some(cat => cat.length > 0);

  return (
    <div className="w-full max-w-5xl mx-auto mt-8 space-y-6 animate-fade-in-up">
      {/* Header / Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-base-100 rounded-xl p-5 border border-base-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-base-content flex items-center">
            <Brain className="w-5 h-5 text-primary mr-2" />
            AI Profile Insights
          </h2>
          <p className="text-sm text-base-content/70 mt-1">
            Based on <span className="font-medium text-base-content">{filename}</span>
            {uploaded_at && <span className="ml-1 text-xs opacity-70">• Parsed {new Date(uploaded_at).toLocaleDateString()}</span>}
          </p>
        </div>
        <div className="flex items-center space-x-3 mt-4 sm:mt-0">
          <button onClick={onReplace} className="btn btn-sm btn-outline hover:bg-base-200">
            <Upload className="w-4 h-4 mr-2" /> Replace
          </button>
          <button onClick={onRestart} className="btn btn-sm btn-primary">
            <RefreshCw className="w-4 h-4 mr-2" /> Match Jobs
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Skills Section */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-base-100 rounded-xl p-6 border border-base-200 shadow-sm">
            <h3 className="text-lg font-bold text-base-content mb-4 border-b border-base-200 pb-2">Extracted Skills</h3>
            {hasSkills ? (
              <div className="space-y-5">
                {skills.languages?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 flex items-center">
                      <Code className="w-3.5 h-3.5 mr-1" /> Languages
                    </h4>
                    <div className="flex flex-wrap">
                      {skills.languages.map(s => <SkillBadge key={s} skill={s} colorClass="text-blue-600 bg-blue-100 border-blue-200" />)}
                    </div>
                  </div>
                )}
                {skills.frameworks?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 flex items-center">
                      <Code className="w-3.5 h-3.5 mr-1" /> Frameworks
                    </h4>
                    <div className="flex flex-wrap">
                      {skills.frameworks.map(s => <SkillBadge key={s} skill={s} colorClass="text-green-600 bg-green-100 border-green-200" />)}
                    </div>
                  </div>
                )}
                {skills.cloud?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 flex items-center">
                      <Cloud className="w-3.5 h-3.5 mr-1" /> Cloud
                    </h4>
                    <div className="flex flex-wrap">
                      {skills.cloud.map(s => <SkillBadge key={s} skill={s} colorClass="text-purple-600 bg-purple-100 border-purple-200" />)}
                    </div>
                  </div>
                )}
                {skills.databases?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 flex items-center">
                      <Database className="w-3.5 h-3.5 mr-1" /> Databases
                    </h4>
                    <div className="flex flex-wrap">
                      {skills.databases.map(s => <SkillBadge key={s} skill={s} colorClass="text-orange-600 bg-orange-100 border-orange-200" />)}
                    </div>
                  </div>
                )}
                {skills.tools?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 flex items-center">
                      <PenTool className="w-3.5 h-3.5 mr-1" /> Tools
                    </h4>
                    <div className="flex flex-wrap">
                      {skills.tools.map(s => <SkillBadge key={s} skill={s} colorClass="text-gray-600 bg-gray-100 border-gray-200" />)}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-base-200/50 rounded-lg text-center">
                <p className="text-sm text-base-content/60 italic mb-2">We couldn't detect structured technical skills from this resume.</p>
                <p className="text-xs text-base-content/50">Try a cleaner PDF or DOCX format for better results.</p>
              </div>
            )}
          </div>
        </div>

        {/* Roles and Queries Section */}
        <div className="md:col-span-1 space-y-6">
          
          <div className="bg-gradient-to-br from-primary/10 to-transparent rounded-xl p-6 border border-primary/20 shadow-sm relative overflow-hidden">
            <Brain className="absolute -right-4 -top-4 w-24 h-24 text-primary/5 rotate-12 pointer-events-none" />
            <h3 className="text-lg font-bold text-base-content mb-4 border-b border-primary/10 pb-2 relative z-10 flex items-center">
               Top AI Role Matches
            </h3>
            {roles && roles.length > 0 ? (
              <ul className="space-y-4 relative z-10">
                {roles.map((r, i) => (
                  <li key={i} className="flex flex-col">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-base-content flex items-center text-sm">
                        <Briefcase className="w-3.5 h-3.5 mr-1.5 text-primary" /> {r.role}
                      </span>
                      <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">{r.confidence}%</span>
                    </div>
                    <div className="w-full bg-base-200 rounded-full h-1.5 mt-1">
                      <div className="bg-primary h-1.5 rounded-full" style={{ width: `${r.confidence}%` }}></div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-base-content/60 italic">Could not confidently determine roles.</p>
            )}
          </div>

          <div className="bg-base-100 rounded-xl p-6 border border-base-200 shadow-sm">
            <h3 className="text-lg font-bold text-base-content mb-4 border-b border-base-200 pb-2 flex items-center">
               Recommended Queries
            </h3>
            {queries && queries.length > 0 ? (
              <ul className="space-y-2">
                {queries.map((q, i) => (
                  <li key={i} className="flex items-start text-sm text-base-content/80 group">
                    <Search className="w-3.5 h-3.5 mt-0.5 mr-2 text-base-content/40 group-hover:text-primary transition-colors" />
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-base-content/60 italic">No search queries generated.</p>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
};

export default ResumeInsights;
