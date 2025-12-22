"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Search, Download, ExternalLink, Filter, X, FileText, Calendar, User, Tag, ChevronLeft, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { toast } from "sonner";

import { API_BASE } from "@/lib/api";

// Types
interface LibraryDocument {
    title: string;
    year: number | null;
    project_code: string | null;
    author: string | null;
    publisher: string | null;
    date_issued: string | null;
    abstract: string | null;
    category: string | null;
    subject: string | null;
    pdf_url: string | null;
    source_page: string | null;
    filename: string | null;
}

interface LibraryFilters {
    years: number[];
    subjects: string[];
    categories: string[];
}

interface LibraryResponse {
    documents: LibraryDocument[];
    total: number;
    page: number;
    limit: number;
}

const ITEMS_PER_PAGE = 24;

export default function LibraryPage() {
    const [documents, setDocuments] = useState<LibraryDocument[]>([]);
    const [filters, setFilters] = useState<LibraryFilters | null>(null);
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);

    // Search and filter state
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedYear, setSelectedYear] = useState<number | null>(null);
    const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
    const [showFilters, setShowFilters] = useState(false);

    // Fetch filters on mount
    useEffect(() => {
        fetch(`${API_BASE}/library/filters`)
            .then((res) => res.json())
            .then((data) => setFilters(data))
            .catch((err) => {
                console.error(err);
                toast.error("Failed to load filters");
            });
    }, []);

    // Fetch documents
    const fetchDocuments = useCallback(async () => {
        setLoading(true);
        const params = new URLSearchParams();
        if (searchQuery) params.set("q", searchQuery);
        if (selectedYear) params.set("year", selectedYear.toString());
        if (selectedSubject) params.set("subject", selectedSubject);
        params.set("limit", ITEMS_PER_PAGE.toString());
        params.set("page", page.toString());

        try {
            const res = await fetch(`${API_BASE}/library?${params}`);
            const data: LibraryResponse = await res.json();

            setDocuments(data.documents);
            setTotal(data.total);
        } catch (error: any) {
            console.error("Failed to fetch documents:", error);
            toast.error("Failed to load documents");
        } finally {
            setLoading(false);
        }
    }, [searchQuery, selectedYear, selectedSubject, page]);

    // Initial fetch and filter changes
    useEffect(() => {
        // Reset to page 1 when filters change, but not when page changes
        setPage(1);
    }, [searchQuery, selectedYear, selectedSubject]);

    // Fetch when page or filters (via effect above resetting page) change
    // We need to decouple the page reset from the fetch to avoid double fetching or complex deps.
    // Actually, simpler: 
    // 1. Filter change -> setPage(1)
    // 2. Page change OR Filter change -> Fetch?
    // Let's use a separate effect for the fetch.
    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);


    // Handle search submit
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchDocuments();
    };

    // Clear all filters
    const clearFilters = () => {
        setSearchQuery("");
        setSelectedYear(null);
        setSelectedSubject(null);
        setPage(1);
    };

    const hasActiveFilters = searchQuery || selectedYear || selectedSubject;
    const totalPages = Math.ceil(total / ITEMS_PER_PAGE);

    // Animation variants
    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.05 },
        },
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 },
    };

    return (
        <div className="min-h-screen bg-background pb-12">
            {/* Header */}
            <div className="sticky top-0 z-10 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b dark:border-slate-700">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <Link href="/">
                                <img src="/logo.png" alt="CRDC Logo" className="h-8 w-auto dark:invert" />
                            </Link>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-heading">Research Library</h1>
                        </div>
                        <Badge variant="secondary" className="text-sm">
                            {total} Documents
                        </Badge>
                    </div>

                    {/* Search Bar */}
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                            <Input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search by title, author, or topic..."
                                className="pl-10 h-12 text-lg rounded-xl bg-slate-100 dark:bg-slate-800 border-none dark:text-white dark:placeholder:text-slate-400"
                            />
                        </div>
                        <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-12 w-12 rounded-xl"
                            onClick={() => setShowFilters(!showFilters)}
                        >
                            <Filter className={`h-5 w-5 ${showFilters ? "text-[#692080]" : ""}`} />
                        </Button>
                        <Button
                            type="submit"
                            className="h-12 px-6 rounded-xl bg-[#692080] hover:bg-[#501860]"
                        >
                            Search
                        </Button>
                    </form>

                    {/* Filter Pills */}
                    {showFilters && filters && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-4 space-y-3"
                        >
                            {/* Year Filter */}
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-sm font-medium text-slate-600 flex items-center gap-1">
                                    <Calendar className="h-4 w-4" /> Year:
                                </span>
                                {filters.years.map((year) => (
                                    <Badge
                                        key={year}
                                        variant={selectedYear === year ? "default" : "outline"}
                                        className={`cursor-pointer transition-all ${selectedYear === year
                                            ? "bg-[#692080] hover:bg-[#501860]"
                                            : "hover:bg-slate-100"
                                            }`}
                                        onClick={() => setSelectedYear(selectedYear === year ? null : year)}
                                    >
                                        {year}
                                    </Badge>
                                ))}
                            </div>

                            {/* Subject Filter */}
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-sm font-medium text-slate-600 flex items-center gap-1">
                                    <Tag className="h-4 w-4" /> Subject:
                                </span>
                                {filters.subjects.slice(0, 15).map((subject) => (
                                    <Badge
                                        key={subject}
                                        variant={selectedSubject === subject ? "default" : "outline"}
                                        className={`cursor-pointer transition-all ${selectedSubject === subject
                                            ? "bg-[#692080] hover:bg-[#501860]"
                                            : "hover:bg-slate-100"
                                            }`}
                                        onClick={() => setSelectedSubject(selectedSubject === subject ? null : subject)}
                                    >
                                        {subject}
                                    </Badge>
                                ))}
                                {filters.subjects.length > 15 && (
                                    <span className="text-xs text-slate-400">+{filters.subjects.length - 15} more</span>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {/* Active Filters Display */}
                    {hasActiveFilters && (
                        <div className="mt-3 flex items-center gap-2">
                            <span className="text-sm text-slate-500">Active filters:</span>
                            {searchQuery && (
                                <Badge variant="secondary" className="gap-1">
                                    &quot;{searchQuery}&quot;
                                    <X className="h-3 w-3 cursor-pointer" onClick={() => setSearchQuery("")} />
                                </Badge>
                            )}
                            {selectedYear && (
                                <Badge variant="secondary" className="gap-1">
                                    Year: {selectedYear}
                                    <X className="h-3 w-3 cursor-pointer" onClick={() => setSelectedYear(null)} />
                                </Badge>
                            )}
                            {selectedSubject && (
                                <Badge variant="secondary" className="gap-1">
                                    {selectedSubject}
                                    <X className="h-3 w-3 cursor-pointer" onClick={() => setSelectedSubject(null)} />
                                </Badge>
                            )}
                            <Button variant="ghost" size="sm" onClick={clearFilters} className="text-xs text-slate-500">
                                Clear all
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            {/* Document Grid */}
            <div className="max-w-7xl mx-auto px-4 py-6">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-64 rounded-xl bg-slate-100 animate-pulse" />
                        ))}
                    </div>
                ) : documents.length === 0 ? (
                    <div className="text-center py-12">
                        <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-slate-600">No documents found</h3>
                        <p className="text-slate-400">Try adjusting your search or filters</p>
                    </div>
                ) : (
                    <>
                        <motion.div
                            variants={container}
                            initial="hidden"
                            animate="show"
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                        >
                            {documents.map((doc, index) => (
                                <motion.div key={`${doc.filename}-${index}`} variants={item}>
                                    <Card className="h-full hover:shadow-lg transition-all duration-300 border-slate-200 dark:border-slate-700 dark:bg-slate-800 hover:border-[#692080]/30 group">
                                        <CardHeader className="pb-2">
                                            <div className="flex items-start justify-between gap-2">
                                                <CardTitle className="text-base font-semibold text-slate-800 dark:text-white line-clamp-2 group-hover:text-[#692080] dark:group-hover:text-purple-400 transition-colors">
                                                    {doc.title}
                                                </CardTitle>
                                                <FileText className="h-5 w-5 text-slate-400 flex-shrink-0" />
                                            </div>
                                            <CardDescription className="flex items-center gap-2 text-xs dark:text-slate-400">
                                                {doc.year && (
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="h-3 w-3" /> {doc.year}
                                                    </span>
                                                )}
                                                {doc.author && (
                                                    <span className="flex items-center gap-1 truncate">
                                                        <User className="h-3 w-3" /> {doc.author.split(",")[0]}
                                                    </span>
                                                )}
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent className="pt-0">
                                            {/* Subject Tags */}
                                            {doc.subject && (
                                                <div className="flex flex-wrap gap-1 mb-3">
                                                    {doc.subject.split(",").slice(0, 3).map((subj, i) => (
                                                        <Badge
                                                            key={i}
                                                            variant="outline"
                                                            className="text-xs bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700"
                                                        >
                                                            {subj.trim()}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Abstract Preview */}
                                            {doc.abstract && (
                                                <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-3 mb-4">
                                                    {doc.abstract}
                                                </p>
                                            )}

                                            {/* Action Buttons */}
                                            <div className="flex gap-2 mt-auto">
                                                {doc.pdf_url && (
                                                    <>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            className="flex-1 text-xs dark:border-slate-600 dark:text-slate-300"
                                                            asChild
                                                        >
                                                            <a
                                                                href={`${API_BASE.replace('/api', '')}${doc.pdf_url}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            >
                                                                <ExternalLink className="h-3 w-3 mr-1" />
                                                                View PDF
                                                            </a>
                                                        </Button>
                                                    </>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </motion.div>
                            ))}
                        </motion.div>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-center gap-4 mt-8">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="dark:border-slate-700"
                                >
                                    <ChevronLeft className="h-4 w-4 mr-1" />
                                    Previous
                                </Button>
                                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                                    Page {page} of {totalPages}
                                </span>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="dark:border-slate-700"
                                >
                                    Next
                                    <ChevronRight className="h-4 w-4 ml-1" />
                                </Button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
