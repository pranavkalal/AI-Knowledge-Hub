"use client";

import { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Configure worker
// Use unpkg for the matching version (5.4.296)
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFRendererProps {
    url: string;
    page: number;
    bbox?: number[]; // [x, y, width, height] in PDF coordinates
    scale: number;
    onLoadSuccess?: (numPages: number) => void;
}

export function PDFRenderer({ url, page, bbox, scale, onLoadSuccess }: PDFRendererProps) {
    const [numPages, setNumPages] = useState<number | null>(null);
    const [pageWidth, setPageWidth] = useState<number>(0);
    const [pageHeight, setPageHeight] = useState<number>(0);

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
        setNumPages(numPages);
        if (onLoadSuccess) onLoadSuccess(numPages);
    }

    function onPageLoadSuccess(page: any) {
        setPageWidth(page.originalWidth);
        setPageHeight(page.originalHeight);
    }

    return (
        <div className="relative inline-block shadow-lg">
            <Document
                file={url}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={
                    <div className="flex items-center justify-center h-96 w-[600px] bg-slate-100 text-slate-400">
                        Loading PDF...
                    </div>
                }
                error={
                    <div className="flex items-center justify-center h-96 w-[600px] bg-red-50 text-red-400">
                        Failed to load PDF
                    </div>
                }
            >
                <Page
                    pageNumber={page}
                    scale={scale}
                    onLoadSuccess={onPageLoadSuccess}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    className="border bg-white"
                />
            </Document>

            {/* Bbox Highlight Overlay */}
            {bbox && pageWidth > 0 && (
                <div
                    className="absolute border-2 border-emerald-500 bg-emerald-500/20 pointer-events-none transition-all duration-300"
                    style={{
                        left: `${bbox[0] * scale}px`,
                        // PDF coordinates are usually bottom-left origin, but Docling might normalize.
                        // If standard PDF coords (bottom-left): top = pageHeight - y - height
                        // If top-left origin (Docling/HTML-like): top = y
                        // We'll assume Docling provides top-left based on previous analysis, 
                        // but if it's bottom-left, we'd need: top: `${(pageHeight - bbox[1] - bbox[3]) * scale}px`
                        top: `${bbox[1] * scale}px`,
                        width: `${bbox[2] * scale}px`,
                        height: `${bbox[3] * scale}px`,
                    }}
                />
            )}
        </div>
    );
}
