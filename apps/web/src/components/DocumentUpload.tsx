import React, { useState, useCallback, useRef } from "react";
import {
  Upload,
  File,
  X,
  Check,
  AlertCircle,
  FileText,
  Image,
  Database,
  Archive,
  Brain,
  Eye,
  Trash2,
  Download,
} from "lucide-react";

const DocumentUpload = () => {
  const [files, setFiles] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const supportedTypes = {
    "application/pdf": { icon: FileText, color: "text-red-500", name: "PDF" },
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
      icon: FileText,
      color: "text-blue-500",
      name: "Word",
    },
    "text/plain": { icon: FileText, color: "text-gray-500", name: "Text" },
    "text/markdown": {
      icon: FileText,
      color: "text-purple-500",
      name: "Markdown",
    },
    "text/csv": { icon: Database, color: "text-green-500", name: "CSV" },
    "application/json": {
      icon: Database,
      color: "text-yellow-500",
      name: "JSON",
    },
    "application/vnd.ms-excel": {
      icon: Database,
      color: "text-green-600",
      name: "Excel",
    },
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
      icon: Database,
      color: "text-green-600",
      name: "Excel",
    },
  };

  // จำลองข้อมูลไฟล์ที่มีอยู่
  const [existingFiles, setExistingFiles] = useState([
    {
      id: 1,
      name: "quarterly_report.pdf",
      type: "application/pdf",
      size: 2456789,
      chunks: 45,
      uploadDate: "2024-01-15",
      status: "processed",
    },
    {
      id: 2,
      name: "meeting_notes.docx",
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      size: 156234,
      chunks: 12,
      uploadDate: "2024-01-14",
      status: "processed",
    },
    {
      id: 3,
      name: "sales_data.csv",
      type: "text/csv",
      size: 89456,
      chunks: 8,
      uploadDate: "2024-01-13",
      status: "processing",
    },
  ]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Sanitize file name to prevent XSS
  const sanitizeFileName = (name: string): string => {
    return name.replace(/[<>"/\\|?*]/g, '').substring(0, 255);
  };

  const getFileIcon = (type: string) => {
    const fileType = supportedTypes[type as keyof typeof supportedTypes];
    if (fileType) {
      const Icon = fileType.icon;
      return <Icon className={`w-8 h-8 ${fileType.color}`} />;
    }
    return <File className="w-8 h-8 text-gray-400" />;
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  }, []);

  const handleFiles = (fileList: FileList) => {
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB limit
    const newFiles = Array.from(fileList).map((file, index) => ({
      id: Date.now() + index,
      file: file,
      name: sanitizeFileName(file.name),
      size: file.size,
      type: file.type,
      status: "pending", // pending, uploading, processing, completed, error
      progress: 0,
      chunks: 0,
      preview: null,
    }));

    // ตรวจสอบไฟล์ที่รองรับและขนาดไฟล์
    const validFiles = newFiles.filter(
      (file) =>
        file.size <= MAX_FILE_SIZE &&
        (Object.keys(supportedTypes).includes(file.type) ||
        file.name.endsWith(".md")),
    );

    if (validFiles.length !== newFiles.length) {
      const oversizedFiles = newFiles.filter(file => file.size > MAX_FILE_SIZE);
      const unsupportedFiles = newFiles.filter(file =>
        file.size <= MAX_FILE_SIZE &&
        !Object.keys(supportedTypes).includes(file.type) &&
        !file.name.endsWith(".md")
      );

      let errorMessage = "";
      if (oversizedFiles.length > 0) {
        errorMessage += `ไฟล์บางไฟล์มีขนาดใหญ่เกิน 50MB: ${oversizedFiles.map(f => f.name).join(", ")}\n`;
      }
      if (unsupportedFiles.length > 0) {
        errorMessage += `ไฟล์บางไฟล์ไม่ได้รับการรองรับ: ${unsupportedFiles.map(f => f.name).join(", ")}`;
      }
      alert(errorMessage || "บางไฟล์ไม่ได้รับการรองรับ");
    }

    setFiles((prev) => [...prev, ...validFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (id: number) => {
    setFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const startUpload = async () => {
    setUploading(true);

    for (let file of files) {
      if (file.status === "pending") {
        // อัปเดตสถานะเป็น uploading
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id ? { ...f, status: "uploading" } : f,
          ),
        );

        // จำลองการอัปโหลด
        for (let i = 0; i <= 100; i += 10) {
          await new Promise((resolve) => setTimeout(resolve, 100));
          setFiles((prev) =>
            prev.map((f) => (f.id === file.id ? { ...f, progress: i } : f)),
          );
        }

        // เปลี่ยนเป็น processing
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? { ...f, status: "processing", progress: 100 }
              : f,
          ),
        );

        // จำลองการประมวลผล
        await new Promise((resolve) => setTimeout(resolve, 2000));

        const chunks =
          Math.floor(file.size / 1000) + Math.floor(Math.random() * 20);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? { ...f, status: "completed", chunks: chunks }
              : f,
          ),
        );
      }
    }

    setUploading(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <Check className="w-5 h-5 text-green-500" />;
      case "uploading":
      case "processing":
        return (
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        );
      case "error":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Upload className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "ประมวลผลสำเร็จ";
      case "processing":
        return "กำลังประมวลผล...";
      case "uploading":
        return "กำลังอัปโหลด...";
      case "error":
        return "เกิดข้อผิดพลาด";
      default:
        return "พร้อมอัปโหลด";
    }
  };

  const deleteExistingFile = (id: number) => {
    setExistingFiles((prev) => prev.filter((file) => file.id !== id));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            อัปโหลดเอกสาร
          </h1>
          <p className="text-gray-600">
            ลากไฟล์มาวางหรือเลือกเพื่ออัปโหลดเอกสารสู่ระบบ RAG
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Drag & Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
                dragActive
                  ? "border-blue-400 bg-blue-50"
                  : "border-gray-300 hover:border-gray-400"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                onChange={handleFileInput}
                accept=".pdf,.docx,.txt,.md,.csv,.json,.xlsx,.xls"
                className="hidden"
              />

              <div className="space-y-4">
                <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                  <Upload className="w-8 h-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    ลากไฟล์มาวางที่นี่
                  </h3>
                  <p className="text-gray-600 mb-4">
                    หรือ{" "}
                    <button
                      onClick={() =>
                        (
                          inputRef.current as unknown as HTMLInputElement
                        )?.click()
                      }
                      className="text-blue-600 hover:text-blue-700 font-medium"
                    >
                      เลือกไฟล์จากเครื่อง
                    </button>
                  </p>
                  <div className="text-sm text-gray-500">
                    รองรับไฟล์: PDF, Word, Excel, CSV, JSON, Text, Markdown
                    <br />
                    ขนาดไฟล์สูงสุด: 50MB ต่อไฟล์
                  </div>
                </div>
              </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm">
                <div className="p-6 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">
                      ไฟล์ที่เลือก ({files.length})
                    </h3>
                    <button
                      onClick={startUpload}
                      disabled={
                        uploading ||
                        files.every((f) => f.status === "completed")
                      }
                      className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                    >
                      <Upload className="w-5 h-5" />
                      <span>
                        {uploading ? "กำลังอัปโหลด..." : "เริ่มอัปโหลด"}
                      </span>
                    </button>
                  </div>
                </div>
                <div className="p-6 space-y-4">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-shrink-0">
                        {getFileIcon(file.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {file.name}
                          </h4>
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(file.status)}
                            <button
                              onClick={() => removeFile(file.id)}
                              className="text-gray-400 hover:text-red-500 transition-colors"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-sm text-gray-500">
                          <span>{formatFileSize(file.size)}</span>
                          <span>{getStatusText(file.status)}</span>
                        </div>
                        {file.status === "uploading" && (
                          <div className="mt-2">
                            <div className="bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${file.progress}%` }}
                              ></div>
                            </div>
                          </div>
                        )}
                        {file.status === "completed" && (
                          <div className="mt-1 text-sm text-green-600">
                            ประมวลผลแล้ว {file.chunks} chunks
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Upload Stats */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                สถิติการอัปโหลด
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">ไฟล์ที่เลือก</span>
                  <span className="font-semibold text-blue-600">
                    {files.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">ขนาดรวม</span>
                  <span className="font-semibold">
                    {formatFileSize(
                      files.reduce((total, file) => total + file.size, 0),
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">สำเร็จแล้ว</span>
                  <span className="font-semibold text-green-600">
                    {files.filter((f) => f.status === "completed").length}
                  </span>
                </div>
              </div>
            </div>

            {/* Supported Formats */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                รูปแบบที่รองรับ
              </h3>
              <div className="space-y-3">
                {Object.entries(supportedTypes)
                  .slice(0, 6)
                  .map(([type, info]) => (
                    <div key={type} className="flex items-center space-x-3">
                      <info.icon className={`w-5 h-5 ${info.color}`} />
                      <span className="text-sm text-gray-700">{info.name}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* Quick Tips */}
            <div className="bg-blue-50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                💡 เคล็ดลับ
              </h3>
              <ul className="text-sm text-blue-800 space-y-2">
                <li>• ไฟล์ที่มีขนาดใหญ่จะใช้เวลาประมวลผลนานกว่า</li>
                <li>• PDF และ Word ให้ผลลัพธ์ที่ดีที่สุด</li>
                <li>• CSV และ JSON เหมาะสำหรับข้อมูลเชิงตัวเลข</li>
                <li>• ชื่อไฟล์ควรเป็นภาษาอังกฤษ</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Existing Files */}
        {existingFiles.length > 0 && (
          <div className="mt-12">
            <div className="bg-white rounded-xl shadow-sm">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">
                  เอกสารที่มีอยู่ในระบบ
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  จัดการเอกสารที่อัปโหลดไว้แล้ว
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ไฟล์
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ขนาด
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Chunks
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        วันที่อัปโหลด
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        สถานะ
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        การจัดการ
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {existingFiles.map((file) => (
                      <tr key={file.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-3">
                            <div className="flex-shrink-0">
                              {getFileIcon(file.type)}
                            </div>
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {file.name}
                              </div>
                              <div className="text-sm text-gray-500">
                                {supportedTypes[
                                  file.type as keyof typeof supportedTypes
                                ]?.name || "Unknown"}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatFileSize(file.size)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {file.chunks} chunks
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {file.uploadDate}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              file.status === "processed"
                                ? "bg-green-100 text-green-800"
                                : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {file.status === "processed"
                              ? "ประมวลผลแล้ว"
                              : "กำลังประมวลผล"}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex items-center space-x-2">
                            <button
                              aria-label="View file"
                              className="text-blue-600 hover:text-blue-700 p-1"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              aria-label="Download file"
                              className="text-gray-600 hover:text-gray-700 p-1"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => deleteExistingFile(file.id)}
                              aria-label="Delete file"
                              className="text-red-600 hover:text-red-700 p-1"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentUpload;
