import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getResume, deleteResume } from '../services/resumeApi';
import ResumeUpload from '../components/ResumeUpload';
import ResumeInsights from '../components/ResumeInsights';
import PageHeader from '../components/PageHeader';
import { CheckCircle, Loader2 } from 'lucide-react';
import { socket } from '../services/socket';

const ResumePage = () => {
  const [resumeData, setResumeData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);
  const navigate = useNavigate();
  const fetchAttempted = useRef(false);

  useEffect(() => {
    if (fetchAttempted.current) return;
    fetchAttempted.current = true;
    fetchResume();
  }, []);

  useEffect(() => {
    const handleParsingComplete = (data) => {
      toast.success("Resume parsed successfully!");
      setResumeData(prev => ({
         ...prev,
         skills: data.skills,
         roles: data.roles,
         queries: data.queries,
         status: 'completed',
         parsing_status: 'completed'
      }));
    };

    const handleParsingFailed = (data) => {
      toast.error(`Parsing failed: ${data.error}`);
      setResumeData(null); // back to upload screen
    };

    socket.on('parsing:complete', handleParsingComplete);
    socket.on('parsing:failed', handleParsingFailed);

    return () => {
      socket.off('parsing:complete', handleParsingComplete);
      socket.off('parsing:failed', handleParsingFailed);
    };
  }, []);

  const fetchResume = async () => {
    setIsLoading(true);
    try {
      const response = await getResume();
      if (response.success && response.data?.filename) {
        setResumeData(response.data);
      } else {
        setResumeData(null);
      }
    } catch (error) {
      console.error('Failed to fetch resume:', error);
      toast.error('Failed to load resume profile.');
      setResumeData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadSuccess = (data) => {
    setResumeData(data);
    setShowSuccessBanner(true);
    setTimeout(() => setShowSuccessBanner(false), 5000);
  };

  const handleReplace = () => {
    setResumeData(null); // Show upload screen, actual file replacement happens on new upload
  };

  const handleRestartMatching = () => {
    toast.success('Matching pipeline is active. Generating new strategies...');
    // We navigate to the dashboard or queue where matching happens
    navigate('/'); // Assuming '/' is the dashboard based on common routing, or maybe trigger cycle API
  };

  return (
    <div className="w-full h-full p-4 md:p-6 overflow-y-auto" style={{ background: 'transparent' }}>
      <div className="max-w-6xl mx-auto">
        <PageHeader 
          title="AI Career Copilot" 
          subtitle="Your personalized AI job search assistant begins here. We extract your skills and autonomously apply to perfectly matched roles."
        />

        <div className="mt-8">
          {showSuccessBanner && (
            <div className="mb-6 p-4 bg-success/10 border border-success/20 rounded-xl flex items-center text-success animate-fade-in-down">
              <CheckCircle className="w-5 h-5 mr-3" />
              <span className="font-medium">AI matching pipeline started successfully. Your profile is ready.</span>
            </div>
          )}

          {isLoading ? (
            <div className="w-full max-w-2xl mx-auto">
              <div className="animate-pulse flex flex-col items-center justify-center space-y-6 py-12 border-2 border-dashed border-base-300 rounded-xl">
                 <div className="w-16 h-16 bg-base-300 rounded-full"></div>
                 <div className="h-6 bg-base-300 rounded w-1/3"></div>
                 <div className="h-4 bg-base-300 rounded w-2/3"></div>
              </div>
            </div>
          ) : resumeData?.status === 'parsing' || resumeData?.parsing_status === 'parsing' ? (
            <div className="w-full max-w-2xl mx-auto flex flex-col items-center justify-center p-12 bg-base-100 rounded-xl border border-base-200 shadow-sm animate-fade-in-up">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full"></div>
                <Loader2 className="w-16 h-16 text-primary animate-spin relative z-10" />
              </div>
              <h3 className="text-xl font-bold text-base-content mb-2">AI is analyzing your resume</h3>
              <p className="text-sm text-base-content/60 text-center max-w-md">
                Extracting technical skills, detecting your strongest roles, and generating matching queries. This usually takes a few seconds...
              </p>
            </div>
          ) : resumeData ? (
            <ResumeInsights 
              data={resumeData} 
              onReplace={handleReplace}
              onRestart={handleRestartMatching}
            />
          ) : (
            <ResumeUpload onUploadSuccess={handleUploadSuccess} />
          )}
        </div>
      </div>
    </div>
  );
};

export default ResumePage;
