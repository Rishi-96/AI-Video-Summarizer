import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState('Checking...');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [files, setFiles] = useState([]);

  // Check backend health on load
  useEffect(() => {
    checkBackendHealth();
    loadFiles();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/health');
      const data = await response.json();
      setBackendStatus(data.status);
    } catch (error) {
      setBackendStatus('Offline');
    }
  };

  const loadFiles = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/files');
      const data = await response.json();
      setFiles(data.files || []);
    } catch (error) {
      console.error('Error loading files:', error);
    }
  };

  const handleFileSelect = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    setUploading(true);
    setUploadProgress(0);

    // Simulate progress (since fetch doesn't provide upload progress easily)
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 10;
      });
    }, 500);

    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      clearInterval(interval);
      setUploadProgress(100);
      setUploadResult(result);
      
      // Refresh file list
      setTimeout(() => {
        loadFiles();
      }, 1000);
      
    } catch (error) {
      clearInterval(interval);
      console.error('Upload error:', error);
      alert('Upload failed: ' + error.message);
    } finally {
      setTimeout(() => {
        setUploading(false);
      }, 1000);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎬 AI Video Summarizer</h1>
        <p>Backend Status: 
          <span style={{ 
            color: backendStatus === 'healthy' ? '#4caf50' : '#f44336',
            marginLeft: '10px',
            fontWeight: 'bold'
          }}>
            {backendStatus}
          </span>
        </p>
      </header>

      <main style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        {/* Upload Section */}
        <div style={{
          border: '2px dashed #61dafb',
          borderRadius: '10px',
          padding: '30px',
          textAlign: 'center',
          marginBottom: '30px'
        }}>
          <h2>Upload Video</h2>
          <input
            type="file"
            accept="video/*"
            onChange={handleFileSelect}
            disabled={uploading}
            style={{ marginBottom: '20px' }}
          />
          <br />
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            style={{
              padding: '10px 30px',
              fontSize: '16px',
              backgroundColor: '#61dafb',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            {uploading ? 'Uploading...' : 'Upload Video'}
          </button>

          {uploading && (
            <div style={{ marginTop: '20px' }}>
              <div style={{
                width: '100%',
                height: '20px',
                backgroundColor: '#e0e0e0',
                borderRadius: '10px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: uploadProgress + '%',
                  height: '100%',
                  backgroundColor: '#4caf50',
                  transition: 'width 0.3s'
                }} />
              </div>
              <p>{uploadProgress}% uploaded</p>
            </div>
          )}

          {uploadResult && (
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: '#4caf50',
              color: 'white',
              borderRadius: '5px'
            }}>
              <p>✅ Upload Successful!</p>
              <p>File: {uploadResult.original_name}</p>
              <p>Size: {uploadResult.size_mb} MB</p>
            </div>
          )}
        </div>

        {/* Files List Section */}
        <div style={{
          border: '1px solid #61dafb',
          borderRadius: '10px',
          padding: '20px'
        }}>
          <h2>Uploaded Videos</h2>
          {files.length === 0 ? (
            <p style={{ color: '#888' }}>No videos uploaded yet</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {files.map((file, index) => (
                <li key={index} style={{
                  padding: '10px',
                  borderBottom: '1px solid #333',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>📹 {file.filename}</span>
                  <span style={{ color: '#888' }}>{file.size_mb} MB</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;