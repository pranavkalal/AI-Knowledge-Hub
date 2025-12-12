import React from "react";

export default function AboutPage() {
    return (
        <div className="container mx-auto max-w-4xl px-4 py-12">
            <h1 className="mb-8 text-4xl font-bold tracking-tight text-slate-900">
                About the <span className="text-[#692080]">Knowledge Hub</span>
            </h1>

            <div className="prose prose-lg prose-slate max-w-none">
                <p className="lead text-xl text-slate-600">
                    The CRDC Knowledge Hub is an AI-powered research assistant designed to unlock the wealth of information contained within Australian cotton industry reports.
                </p>

                <h2 className="mt-8 text-2xl font-semibold text-slate-800">Our Mission</h2>
                <p>
                    The Cotton Research and Development Corporation (CRDC) invests in world-class research to ensure the Australian cotton industry remains sustainable, competitive, and profitable. This platform aims to make that research more accessible, searchable, and actionable for growers, agronomists, and researchers.
                </p>

                <h2 className="mt-8 text-2xl font-semibold text-slate-800">How It Works</h2>
                <p>
                    We use advanced Retrieval-Augmented Generation (RAG) technology to:
                </p>
                <ul className="list-disc pl-6">
                    <li><strong>Ingest</strong> thousands of PDF reports, technical papers, and fact sheets.</li>
                    <li><strong>Index</strong> the content semantically, understanding the meaning behind the text, not just keywords.</li>
                    <li><strong>Retrieve</strong> the most relevant passages when you ask a question.</li>
                    <li><strong>Generate</strong> a concise, cited answer using a Large Language Model (LLM).</li>
                </ul>

                <h2 className="mt-8 text-2xl font-semibold text-slate-800">Transparency & Trust</h2>
                <p>
                    Every answer provided by the Knowledge Hub includes direct citations to the source documents. We believe in transparency—you should always be able to verify the information and dive deeper into the original research.
                </p>
            </div>
        </div>
    );
}
