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

    // Debug logging
    useEffect(() => {
        console.log(`[PDFRenderer] bbox received:`, bbox);
        console.log(`[PDFRenderer] pageWidth:`, pageWidth, 'scale:', scale);
        if (bbox && pageWidth > 0) {
            console.log(`[PDFRenderer] Would render highlight at:`, {
                left: bbox[0] * scale,
                top: bbox[1] * scale,
                width: bbox[2] * scale,
                height: bbox[3] * scale
            });
        }
    }, [bbox, pageWidth, scale]);

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
                    className="absolute border-2 border-purple-500 bg-purple-500/20 pointer-events-none animate-pulse z-50"
                    style={{
                        left: `${bbox[0] * scale}px`,
                        top: `${bbox[1] * scale}px`,
                        width: `${Math.max(bbox[2] * scale, 50)}px`,
                        height: `${Math.max(bbox[3] * scale, 20)}px`,
                    }}
                />
            )}
        </div>
    );
}
