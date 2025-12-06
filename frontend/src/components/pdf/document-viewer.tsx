"use client";

import { Button } from "@/components/ui/button";
import { X, Maximize2, ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from "lucide-react";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

interface DocumentViewerProps {
    docId: string;
    page?: number;
    bbox?: number[];  // [x, y, width, height]
    onClose: () => void;
}

export function DocumentViewer({ docId, page = 1, bbox, onClose }: DocumentViewerProps) {
    const [currentPage, setCurrentPage] = useState(page);
    const [zoom, setZoom] = useState(100);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);

    useEffect(() => {
        console.log(`[DocumentViewer] Props received:`, { docId, page, bbox });
        console.log(`[DocumentViewer] bbox type:`, typeof bbox, Array.isArray(bbox));
        if (bbox) {
            console.log(`[DocumentViewer] bbox values: x=${bbox[0]}, y=${bbox[1]}, w=${bbox[2]}, h=${bbox[3]}`);
        }

        // Construct PDF URL
        // Assuming backend is at 127.0.0.1:8000 based on setup
        // In production, this should use an env var
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        setPdfUrl(`${baseUrl}/pdf/by-id/${docId}`);

        if (page) {
            setCurrentPage(page);
        }
    }, [docId, page, bbox]);

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 200));
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 50));
    const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
    const handleNextPage = () => setCurrentPage(prev => prev + 1);

    // Callback when PDF page loads to update page count if needed
    // For now we just handle rendering

    // Dynamic import for PDFRenderer to avoid SSR issues with canvas
    // But since we are in "use client" component, we can try direct import first.
    // If it fails, we'll need next/dynamic.
    // For now, let's assume standard import works with react-pdf 9+ in Next.js 14 app dir if configured right.
    // We'll use a dynamic import wrapper in the file if needed, but let's try importing PDFRenderer.

    return (
        <div className="flex h-full flex-col bg-slate-50 border-l">
            {/* Toolbar */}
            <div className="flex items-center justify-between border-b bg-white p-2 px-4 gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-medium text-slate-700 whitespace-nowrap">Source Viewer</span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500 truncate" title={docId}>
                        {docId}
                    </span>
                    {page && (
                        <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 font-medium whitespace-nowrap">
                            Page {currentPage}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {/* Page Navigation */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handlePrevPage}
                        disabled={currentPage <= 1}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-xs text-slate-600 px-2">
                        {currentPage}
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleNextPage}
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>

                    {/* Zoom Controls */}
                    <div className="h-4 w-px bg-slate-200 mx-1" />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleZoomOut}
                        disabled={zoom <= 50}
                    >
                        <ZoomOut className="h-4 w-4" />
                    </Button>
                    <span className="text-xs text-slate-600 px-1 min-w-[3rem] text-center">
                        {zoom}%
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleZoomIn}
                        disabled={zoom >= 200}
                    >
                        <ZoomIn className="h-4 w-4" />
                    </Button>

                    <div className="h-4 w-px bg-slate-200 mx-1" />
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Maximize2 className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8 hover:bg-red-100 hover:text-red-600"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* PDF Viewer */}
            <div className="flex-1 overflow-auto p-8 flex items-center justify-center bg-slate-100">
                {pdfUrl ? (
                    <div className="relative bg-white shadow-lg">
                        <PDFRendererWrapper
                            url={pdfUrl}
                            page={currentPage}
                            scale={zoom / 100}
                            bbox={currentPage === page ? bbox : undefined}
                        />
                    </div>
                ) : (
                    <div className="text-slate-400">Loading document...</div>
                )}
            </div>
        </div>
    );
}

// Dynamic import wrapper to avoid SSR issues with react-pdf
const PDFRendererWrapper = dynamic(
    () => import("./pdf-renderer").then((mod) => mod.PDFRenderer),
    {
        ssr: false,
        loading: () => <div className="h-96 w-[600px] flex items-center justify-center bg-white">Loading PDF Renderer...</div>
    }
);
