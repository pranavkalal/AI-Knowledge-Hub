"use client";

import { Button } from "@/components/ui/button";
import { X, Maximize2, ZoomIn, ZoomOut } from "lucide-react";

interface DocumentViewerProps {
    docId: string;
    onClose: () => void;
}

export function DocumentViewer({ docId, onClose }: DocumentViewerProps) {
    return (
        <div className="flex h-full flex-col bg-slate-50 border-l">
            <div className="flex items-center justify-between border-b bg-white p-2 px-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-700">Source Viewer</span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{docId}</span>
                </div>
                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ZoomOut className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ZoomIn className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Maximize2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 hover:bg-red-100 hover:text-red-600">
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>
            <div className="flex-1 overflow-auto p-8 flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="mx-auto h-32 w-24 border bg-white shadow-sm flex items-center justify-center text-slate-300">
                        PDF
                    </div>
                    <p className="text-sm text-slate-500">
                        PDF Viewer Integration Pending<br />
                        (Will load document: {docId})
                    </p>
                </div>
            </div>
        </div>
    );
}
