import { useState, useEffect } from 'react'
import { Upload, Trash2, CheckCircle, Clock, XCircle, FileText } from 'lucide-react'

function DocumentsPage() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/documents/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setDocuments(data)
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const handleFileSelect = (e) => {
    setSelectedFile(e.target.files[0])
  }

  const uploadDocument = async () => {
    if (!selectedFile) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      })

      if (response.ok) {
        setSelectedFile(null)
        fetchDocuments()
      }
    } catch (error) {
      console.error('Error uploading:', error)
    } finally {
      setUploading(false)
    }
  }

  const deleteDocument = async (id) => {
    if (!confirm('Delete this document?')) return

    try {
      await fetch(`http://localhost:8000/api/documents/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      fetchDocuments()
    } catch (error) {
      console.error('Error deleting:', error)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="status-icon completed" size={20} />
      case 'processing':
        return <Clock className="status-icon processing" size={20} />
      case 'failed':
        return <XCircle className="status-icon failed" size={20} />
      default:
        return <Clock className="status-icon pending" size={20} />
    }
  }

  return (
    <div className="documents-page">
      <div className="page-header">
        <h2>Document Management</h2>
        <p>Upload and manage your company documentation</p>
      </div>

      {/* Upload Section */}
      <div className="upload-section">
        <div className="upload-card">
          <Upload size={48} />
          <h3>Upload Document</h3>
          <p>Supported: PDF, TXT, MD, DOCX, PNG, JPG, JPEG</p>
          
          <input
            type="file"
            onChange={handleFileSelect}
            accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.bmp,.tiff"
            id="file-input"
            style={{ display: 'none' }}
          />
          
          <label htmlFor="file-input" className="file-select-btn">
            {selectedFile ? selectedFile.name : 'Choose File'}
          </label>

          <button
            onClick={uploadDocument}
            disabled={!selectedFile || uploading}
            className="upload-btn"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>

      {/* Documents List */}
      <div className="documents-list">
        <h3>Uploaded Documents ({documents.length})</h3>
        
        {documents.length === 0 ? (
          <div className="empty-state">
            <FileText size={64} />
            <p>No documents uploaded yet</p>
          </div>
        ) : (
          <div className="documents-grid">
            {documents.map(doc => (
              <div key={doc.id} className="document-card">
                <div className="document-header">
                  {getStatusIcon(doc.status)}
                  <h4>{doc.title}</h4>
                </div>
                
                <div className="document-info">
                  <p><strong>Filename:</strong> {doc.filename}</p>
                  <p><strong>Chunks:</strong> {doc.chunk_count}</p>
                  <p><strong>Status:</strong> {doc.status}</p>
                  <p className="upload-date">
                    {new Date(doc.uploaded_at).toLocaleString()}
                  </p>
                </div>

                <button
                  onClick={() => deleteDocument(doc.id)}
                  className="delete-btn"
                >
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default DocumentsPage