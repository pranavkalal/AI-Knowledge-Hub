"use client";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Maximize2, Minimize2, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Download, Printer, LayoutGrid, ExternalLink } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

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
    const [numPages, setNumPages] = useState<number | null>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [showThumbnails, setShowThumbnails] = useState(false);

    useEffect(() => {
        // Construct PDF URL
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        setPdfUrl(`${baseUrl}/pdf/by-id/${docId}`);

        if (page) {
            setCurrentPage(page);
        }
    }, [docId, page]);

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 200));
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 50));
    const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
    const handleNextPage = () => setCurrentPage(prev => numPages ? Math.min(prev + 1, numPages) : prev + 1);

    const handleLoadSuccess = useCallback((pages: number) => {
        setNumPages(pages);
    }, []);

    const handleFullscreen = () => {
        const elem = document.querySelector('[data-pdf-viewer]');
        if (!elem) return;

        if (!isFullscreen) {
            if (elem.requestFullscreen) {
                elem.requestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
        setIsFullscreen(!isFullscreen);
    };

    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    const handleDownload = () => {
        if (pdfUrl) {
            window.open(pdfUrl, '_blank');
            toast.success("Download started");
        }
    };

    const handlePrint = () => {
        if (pdfUrl) {
            const printWindow = window.open(pdfUrl, '_blank');
            if (printWindow) {
                printWindow.addEventListener('load', () => {
                    printWindow.print();
                });
            }
        }
    };

    // Generate thumbnail pages (show first 10 or all if less)
    const thumbnailPages = numPages ? Array.from({ length: Math.min(numPages, 20) }, (_, i) => i + 1) : [];

    return (
        <div
            data-pdf-viewer
            className={cn(
                "flex h-full flex-col bg-slate-50 dark:bg-slate-900 border-l dark:border-slate-700",
                isFullscreen && "fixed inset-0 z-50"
            )}
        >
            {/* Toolbar */}
            <div className="flex items-center justify-between border-b dark:border-slate-700 bg-white dark:bg-slate-800 p-2 px-4 gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200 whitespace-nowrap">Source Viewer</span>
                    <span className="rounded bg-slate-100 dark:bg-slate-700 px-2 py-0.5 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[150px]" title={docId}>
                        {docId}
                    </span>
                    {numPages && (
                        <span className="rounded bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-400 font-medium whitespace-nowrap">
                            Page {currentPage} of {numPages}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {/* Thumbnails Toggle */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn("h-8 w-8", showThumbnails && "bg-purple-100 dark:bg-purple-900/30 text-purple-600")}
                        onClick={() => setShowThumbnails(!showThumbnails)}
                        title="Toggle thumbnails"
                    >
                        <LayoutGrid className="h-4 w-4" />
                    </Button>

                    <div className="h-4 w-px bg-slate-200 dark:bg-slate-600 mx-1" />

                    {/* Page Navigation */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handlePrevPage}
                        disabled={currentPage <= 1}
                        title="Previous page"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <input
                        type="number"
                        value={currentPage}
                        onChange={(e) => {
                            const val = parseInt(e.target.value);
                            if (val >= 1 && (!numPages || val <= numPages)) {
                                setCurrentPage(val);
                            }
                        }}
                        className="w-12 text-center text-xs border rounded px-1 py-1 dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                        min={1}
                        max={numPages || undefined}
                    />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleNextPage}
                        disabled={numPages ? currentPage >= numPages : false}
                        title="Next page"
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>

                    {/* Zoom Controls */}
                    <div className="h-4 w-px bg-slate-200 dark:bg-slate-600 mx-1" />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleZoomOut}
                        disabled={zoom <= 50}
                        title="Zoom out"
                    >
                        <ZoomOut className="h-4 w-4" />
                    </Button>
                    <span className="text-xs text-slate-600 dark:text-slate-400 px-1 min-w-[3rem] text-center">
                        {zoom}%
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleZoomIn}
                        disabled={zoom >= 200}
                        title="Zoom in"
                    >
                        <ZoomIn className="h-4 w-4" />
                    </Button>

                    <div className="h-4 w-px bg-slate-200 dark:bg-slate-600 mx-1" />

                    {/* Download & Print & Open in New Tab */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleDownload}
                        title="Download PDF"
                    >
                        <Download className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handlePrint}
                        title="Print"
                    >
                        <Printer className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                            if (pdfUrl) {
                                window.open(pdfUrl, '_blank');
                                toast.success("Opened PDF in new tab");
                            }
                        }}
                        title="Open in new tab"
                    >
                        <ExternalLink className="h-4 w-4" />
                    </Button>

                    <div className="h-4 w-px bg-slate-200 dark:bg-slate-600 mx-1" />

                    {/* Fullscreen */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={handleFullscreen}
                        title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
                    >
                        {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600"
                        title="Close viewer"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Thumbnail Sidebar */}
                {showThumbnails && numPages && (
                    <div className="w-32 border-r dark:border-slate-700 bg-slate-100 dark:bg-slate-800 flex-shrink-0">
                        <ScrollArea className="h-full">
                            <div className="p-2 space-y-2">
                                {thumbnailPages.map((pageNum) => (
                                    <button
                                        key={pageNum}
                                        onClick={() => setCurrentPage(pageNum)}
                                        className={cn(
                                            "w-full aspect-[3/4] rounded border-2 flex items-center justify-center text-xs font-medium transition-all",
                                            currentPage === pageNum
                                                ? "border-purple-500 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                                                : "border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500"
                                        )}
                                    >
                                        {pageNum}
                                    </button>
                                ))}
                                {numPages > 20 && (
                                    <div className="text-center text-xs text-slate-400 dark:text-slate-500 py-2">
                                        +{numPages - 20} more
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    </div>
                )}

                {/* PDF Viewer */}
                <div className="flex-1 overflow-auto p-4 md:p-8 flex items-start justify-center bg-slate-100 dark:bg-slate-900">
                    {pdfUrl ? (
                        <div className="relative bg-white dark:bg-slate-800 shadow-lg rounded-lg overflow-hidden">
                            <PDFRendererWrapper
                                url={pdfUrl}
                                page={currentPage}
                                scale={zoom / 100}
                                bbox={currentPage === page ? bbox : undefined}
                                onLoadSuccess={handleLoadSuccess}
                            />
                        </div>
                    ) : (
                        <div className="text-slate-400 dark:text-slate-500">Loading document...</div>
                    )}
                </div>
            </div>

            {/* Keyboard shortcuts hint */}
            <div className="hidden md:block absolute bottom-4 right-4 text-xs text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-800 px-2 py-1 rounded shadow opacity-50">
                ← → Navigate pages | + - Zoom
            </div>
        </div>
    );
}

// Dynamic import wrapper to avoid SSR issues with react-pdf
const PDFRendererWrapper = dynamic(
    () => import("./pdf-renderer").then((mod) => mod.PDFRenderer),
    {
        ssr: false,
        loading: () => (
            <div className="h-96 w-[600px] flex items-center justify-center bg-white dark:bg-slate-800">
                <div className="flex flex-col items-center gap-2 text-slate-400">
                    <div className="h-8 w-8 border-2 border-slate-300 border-t-purple-500 rounded-full animate-spin" />
                    <span>Loading PDF Renderer...</span>
                </div>
            </div>
        )
    }
);
