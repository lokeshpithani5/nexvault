import React from 'react';
import {
  FileText,
  FileCode,
  FileArchive,
  Image as ImageIcon,
  Film,
  Music,
  Database,
  File,
  Folder,
} from 'lucide-react';

export default function FileIcon({
  filename = '',
  contentType = '',
  isFolder = false,
  size = 20,
  className = '',
}) {
  if (isFolder) {
    return <Folder size={size} style={{ color: '#38bdf8' }} className={className} />;
  }

  const ext = filename.split('.').pop().toLowerCase();

  // Images
  if (['png', 'jpg', 'jpeg', 'svg', 'webp', 'gif'].includes(ext) || contentType.startsWith('image/')) {
    return <ImageIcon size={size} style={{ color: '#06b6d4' }} className={className} />;
  }

  // Videos
  if (['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(ext) || contentType.startsWith('video/')) {
    return <Film size={size} style={{ color: '#f43f5e' }} className={className} />;
  }

  // Audio
  if (['mp3', 'wav', 'flac', 'aac', 'ogg'].includes(ext) || contentType.startsWith('audio/')) {
    return <Music size={size} style={{ color: '#a855f7' }} className={className} />;
  }

  // Code
  if (['js', 'jsx', 'ts', 'tsx', 'py', 'json', 'html', 'css', 'go', 'rs', 'sql', 'sh', 'yaml', 'yml'].includes(ext)) {
    return <FileCode size={size} style={{ color: '#3b82f6' }} className={className} />;
  }

  // Archives
  if (['zip', 'tar', 'gz', '7z', 'rar', 'bz2'].includes(ext)) {
    return <FileArchive size={size} style={{ color: '#eab308' }} className={className} />;
  }

  // Data
  if (['db', 'sqlite', 'parquet', 'csv'].includes(ext)) {
    return <Database size={size} style={{ color: '#10b981' }} className={className} />;
  }

  // Documents
  if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext)) {
    return <FileText size={size} style={{ color: '#60a5fa' }} className={className} />;
  }

  return <File size={size} style={{ color: '#94a3b8' }} className={className} />;
}
