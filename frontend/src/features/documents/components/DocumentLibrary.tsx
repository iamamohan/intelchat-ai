"use client"

import * as React from "react"
import {
  FileText,
  Search,
  Trash2,
  BookOpen,
  Layers,
  UploadCloud
} from "lucide-react"
import { useUploadStore } from "@/store/useUploadStore"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Badge } from "@/components/ui/Badge"
import { Progress } from "@/components/ui/Progress"
import { EmptyState } from "@/components/ui/EmptyState"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { DocumentFile } from "@/types"

export function DocumentLibrary() {
  const { documents, queue, deleteDocument, addFileToQueue, loadDocuments } = useUploadStore()
  const [searchQuery, setSearchQuery] = React.useState("")
  const [selectedDoc, setSelectedDoc] = React.useState<DocumentFile | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // Filter documents based on search query
  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      for (let i = 0; i < files.length; i++) {
        addFileToQueue(files[i])
      }
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (confirm(`Are you sure you want to permanently delete "${name}"?`)) {
      await deleteDocument(id)
      if (selectedDoc?.document_id === id) setSelectedDoc(null)
    }
  }

  // Format file size
  const formatBytes = (bytes: number, decimals = 1) => {
    if (!bytes) return "0 Bytes"
    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ["Bytes", "KB", "MB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i]
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar space-y-6">
      {/* Upload/Queue Progress Section */}
      {queue.length > 0 && (
        <Card className="p-4 border-highlight/20 bg-highlight/5 space-y-3">
          <h3 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5 animate-pulse">
            <UploadCloud className="size-4 text-highlight" /> Active Upload Queue
          </h3>
          <div className="space-y-3">
            {queue.map((item) => (
              <div key={item.id} className="space-y-1.5 text-xs">
                <div className="flex justify-between items-center text-[11px] font-semibold text-secondary-foreground">
                  <span className="truncate max-w-[250px]">{item.name}</span>
                  <span className="text-highlight capitalize">{item.status} ({item.progress}%)</span>
                </div>
                <Progress value={item.progress} variant="primary" />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Toolbar: Search, Filters & Upload Button */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between select-none">
        <div className="relative w-full sm:max-w-md">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by name..."
            className="pl-10 h-10"
          />
          <Search className="size-4 text-muted-foreground absolute left-3.5 top-3" />
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf"
            className="hidden"
            multiple
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            className="w-full sm:w-auto font-semibold bg-foreground text-background"
          >
            Upload File
          </Button>
        </div>
      </div>

      {/* Grid List of indexed Documents */}
      {filteredDocs.length === 0 ? (
        <EmptyState type="no-documents" className="py-16" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 select-none">
          {filteredDocs.map((doc) => (
            <Card
              key={doc.document_id}
              variant="interactive"
              onClick={() => setSelectedDoc(doc)}
              className="p-5 flex flex-col justify-between h-44 group relative overflow-hidden"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="p-2.5 rounded-xl bg-surface border border-border/60 text-highlight">
                    <FileText className="size-5" />
                  </div>
                  <Badge variant="success" size="sm">Ready</Badge>
                </div>
                <div>
                  <h4 className="text-xs font-bold text-foreground truncate group-hover:text-highlight transition-colors max-w-[200px]">
                    {doc.original_filename}
                  </h4>
                  <p className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-1">
                    <span>{formatBytes(doc.file_size)}</span>
                    <span>•</span>
                    <span>{doc.page_count} pages</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-border/20 pt-3 mt-2 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Layers className="size-3" /> {doc.chunk_count} chunks
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(doc.document_id, doc.original_filename)
                  }}
                  className="size-7 text-muted-foreground hover:text-error hover:bg-error/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Document details dialog modal */}
      <Dialog open={!!selectedDoc} onOpenChange={() => setSelectedDoc(null)}>
        <DialogContent className="bg-card border border-border/80 text-foreground rounded-2xl max-w-md p-6 z-50">
          {selectedDoc && (
            <div className="space-y-5 select-none">
              <DialogHeader className="pb-3 border-b border-border/40">
                <DialogTitle className="text-sm font-heading flex items-center gap-2">
                  <BookOpen className="size-4.5 text-highlight" /> Document Properties
                </DialogTitle>
                <DialogDescription className="text-[10px] text-muted-foreground break-all mt-1">
                  ID: {selectedDoc.document_id}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3.5 text-xs text-secondary-foreground font-medium pl-1">
                <div className="flex justify-between">
                  <span>File Name:</span>
                  <span className="text-foreground max-w-[200px] truncate">{selectedDoc.original_filename}</span>
                </div>
                <div className="flex justify-between">
                  <span>File Size:</span>
                  <span className="text-foreground">{formatBytes(selectedDoc.file_size)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Pages:</span>
                  <span className="text-foreground">{selectedDoc.page_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Chunks:</span>
                  <span className="text-foreground">{selectedDoc.chunk_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Vector Embeddings:</span>
                  <span className="text-foreground">{selectedDoc.vector_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Embedding Model:</span>
                  <span className="text-foreground text-[10px] font-mono">{selectedDoc.embedding_model}</span>
                </div>
                <div className="flex justify-between">
                  <span>Indexed Date:</span>
                  <span className="text-foreground">{new Date(selectedDoc.upload_timestamp).toLocaleString()}</span>
                </div>
              </div>

              <div className="pt-4 border-t border-border/40 flex justify-between gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedDoc(null)}
                  className="rounded-lg h-9 w-full font-semibold"
                >
                  Close Properties
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleDelete(selectedDoc.document_id, selectedDoc.original_filename)}
                  className="rounded-lg h-9 w-full font-semibold"
                >
                  Delete Document
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
