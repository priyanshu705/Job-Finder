import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileText, Loader2, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { uploadResume } from '../services/resumeApi';

const ResumeUpload = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleCancel = (e) => {
    e.stopPropagation();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateFile = (file) => {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please upload a PDF, DOCX, DOC, or TXT file.');
      return false;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File size exceeds 5MB limit.');
      return false;
    }
    return true;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileInput = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const processFile = async (file) => {
    if (!validateFile(file)) return;
    
    setIsUploading(true);
    setProgress(0);
    
    try {
      const { promise, abort } = uploadResume(file, (percent) => {
        setProgress(percent);
      });
      abortControllerRef.current = { abort };
      
      const response = await promise;
      
      if (response.success) {
        toast.success(response.message || 'Resume uploaded successfully!');
        if (onUploadSuccess) onUploadSuccess(response.data);
      } else {
        toast.error(response.error?.message || 'Upload failed');
      }
    } catch (err) {
      console.error(err);
      toast.error(err.message || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
      setProgress(0);
      abortControllerRef.current = null;
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-8">
      <div 
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all duration-300 ease-in-out ${
          isDragging ? 'border-primary bg-primary/5' : 'border-base-300 hover:border-primary/50 hover:bg-base-200/50'
        } ${isUploading ? 'pointer-events-none opacity-80' : 'cursor-pointer'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileInput} 
          className="hidden" 
          accept=".pdf,.doc,.docx,.txt"
        />
        
        {isUploading ? (
          <div className="flex flex-col items-center justify-center space-y-4">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <h3 className="text-xl font-semibold text-base-content">Analyzing Resume...</h3>
            <p className="text-sm text-base-content/70 text-center max-w-sm">
              AI is analyzing your experience and generating personalized job strategies...
            </p>
            <div className="w-full max-w-xs bg-base-300 rounded-full h-2.5 mt-4 overflow-hidden">
              <div className="bg-primary h-2.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
            </div>
            <span className="text-xs font-medium text-base-content/50">{progress}%</span>
            <button 
              onClick={handleCancel}
              className="mt-4 inline-flex items-center text-xs font-medium text-error hover:text-error/80 transition-colors pointer-events-auto"
            >
              <XCircle className="w-4 h-4 mr-1" /> Cancel Upload
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="p-4 bg-primary/10 rounded-full text-primary">
              <UploadCloud className="w-10 h-10" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-base-content mb-2">Upload your resume</h3>
              <p className="text-sm text-base-content/70 max-w-sm mx-auto">
                Upload your resume and let AI personalize your career journey. Drag and drop your file here, or click to browse.
              </p>
            </div>
            <div className="flex items-center space-x-2 text-xs font-medium text-base-content/50 bg-base-200 px-3 py-1.5 rounded-full mt-4">
              <FileText className="w-3.5 h-3.5" />
              <span>Supports PDF, DOCX, DOC, TXT (Max 5MB)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResumeUpload;
