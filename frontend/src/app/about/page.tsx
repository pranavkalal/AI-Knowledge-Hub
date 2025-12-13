"use client";

import { motion } from "framer-motion";
import {
    FileText,
    Brain,
    Search,
    MessageSquare,
    Users,
    BookOpen,
    Zap,
    Shield,
    ArrowRight,
    Leaf,
    Mail
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const stats = [
    { value: "2,500+", label: "Research Papers", icon: FileText },
    { value: "15+", label: "Years of Data", icon: BookOpen },
    { value: "100+", label: "Research Topics", icon: Brain },
    { value: "3", label: "User Personas", icon: Users },
];

const steps = [
    {
        icon: FileText,
        title: "Ingest",
        description: "Thousands of PDF reports, technical papers, and fact sheets are processed and parsed.",
    },
    {
        icon: Brain,
        title: "Index",
        description: "Content is indexed semantically, understanding meaning behind the text, not just keywords.",
    },
    {
        icon: Search,
        title: "Retrieve",
        description: "When you ask a question, the most relevant passages are retrieved from the knowledge base.",
    },
    {
        icon: MessageSquare,
        title: "Generate",
        description: "A Large Language Model generates a concise, cited answer based on the retrieved content.",
    },
];

const features = [
    {
        icon: Zap,
        title: "Lightning Fast",
        description: "Get answers in seconds, not hours of manual research.",
    },
    {
        icon: Shield,
        title: "Trustworthy",
        description: "Every answer includes direct citations to source documents.",
    },
    {
        icon: Users,
        title: "Persona-Based",
        description: "Tailored responses for growers, researchers, and extension officers.",
    },
];

export default function AboutPage() {
    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.1 },
        },
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 },
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Hero Section */}
            <section className="relative py-20 px-4">
                <div className="max-w-4xl mx-auto text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                    >
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#692080]/10 text-[#692080] dark:bg-purple-900/30 dark:text-purple-300 text-sm font-medium mb-6">
                            <Leaf className="h-4 w-4" />
                            Powered by AI
                        </div>

                        <h1 className="text-4xl md:text-6xl font-bold text-slate-900 dark:text-white mb-6 font-heading">
                            About the{" "}
                            <span className="text-[#692080] dark:text-purple-400">
                                Knowledge Hub
                            </span>
                        </h1>

                        <p className="text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8">
                            An AI-powered research assistant designed to unlock the wealth of information
                            contained within Australian cotton industry reports.
                        </p>

                        <div className="flex flex-wrap justify-center gap-4">
                            <Link href="/">
                                <Button size="lg" className="bg-[#692080] hover:bg-[#501860] text-lg px-8">
                                    Try It Now
                                    <ArrowRight className="ml-2 h-5 w-5" />
                                </Button>
                            </Link>
                            <Link href="/library">
                                <Button size="lg" variant="outline" className="text-lg px-8 dark:border-slate-600 dark:text-slate-300">
                                    Browse Library
                                </Button>
                            </Link>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="py-16 px-4 bg-slate-50 dark:bg-slate-900/50">
                <motion.div
                    variants={container}
                    initial="hidden"
                    whileInView="show"
                    viewport={{ once: true }}
                    className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8"
                >
                    {stats.map((stat, i) => (
                        <motion.div
                            key={i}
                            variants={item}
                            className="text-center"
                        >
                            <div className="mb-2">
                                <stat.icon className="h-8 w-8 mx-auto text-[#692080] dark:text-purple-400" />
                            </div>
                            <div className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-1">
                                {stat.value}
                            </div>
                            <div className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                                {stat.label}
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            </section>

            {/* Mission Section */}
            <section className="py-20 px-4">
                <div className="max-w-4xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-12"
                    >
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-6 font-heading">
                            Our Mission
                        </h2>
                        <p className="text-lg text-slate-600 dark:text-slate-300 max-w-3xl mx-auto leading-relaxed">
                            The Cotton Research and Development Corporation (CRDC) invests in world-class research
                            to ensure the Australian cotton industry remains sustainable, competitive, and profitable.
                            This platform aims to make that research more accessible, searchable, and actionable
                            for growers, agronomists, and researchers.
                        </p>
                    </motion.div>
                </div>
            </section>

            {/* How It Works Section */}
            <section className="py-20 px-4 bg-slate-50 dark:bg-slate-900/50">
                <div className="max-w-5xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-12"
                    >
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-4 font-heading">
                            How It Works
                        </h2>
                        <p className="text-lg text-slate-600 dark:text-slate-300">
                            Powered by advanced Retrieval-Augmented Generation (RAG)
                        </p>
                    </motion.div>

                    <motion.div
                        variants={container}
                        initial="hidden"
                        whileInView="show"
                        viewport={{ once: true }}
                        className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
                    >
                        {steps.map((step, i) => (
                            <motion.div key={i} variants={item}>
                                <Card className="h-full bg-white dark:bg-slate-800 border-none shadow-sm hover:shadow-md transition-shadow">
                                    <CardContent className="pt-6 text-center">
                                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#692080]/10 mb-4">
                                            <step.icon className="h-6 w-6 text-[#692080] dark:text-purple-400" />
                                        </div>
                                        <div className="text-xs font-bold text-slate-400 dark:text-slate-500 mb-2 uppercase tracking-wider">
                                            Step {i + 1}
                                        </div>
                                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                                            {step.title}
                                        </h3>
                                        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                            {step.description}
                                        </p>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        ))}
                    </motion.div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 px-4">
                <div className="max-w-5xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-4 font-heading">
                            Why Use Knowledge Hub?
                        </h2>
                    </motion.div>

                    <motion.div
                        variants={container}
                        initial="hidden"
                        whileInView="show"
                        viewport={{ once: true }}
                        className="grid md:grid-cols-3 gap-8"
                    >
                        {features.map((feature, i) => (
                            <motion.div
                                key={i}
                                variants={item}
                                className="text-center group"
                            >
                                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 mb-6 group-hover:bg-[#692080]/10 transition-colors duration-300">
                                    <feature.icon className="h-8 w-8 text-slate-700 dark:text-slate-300 group-hover:text-[#692080] dark:group-hover:text-purple-400 transition-colors duration-300" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
                                    {feature.title}
                                </h3>
                                <p className="text-slate-600 dark:text-slate-400 leading-relaxed max-w-sm mx-auto">
                                    {feature.description}
                                </p>
                            </motion.div>
                        ))}
                    </motion.div>
                </div>
            </section>

            {/* Transparency Section */}
            <section className="py-20 px-4 bg-[#692080] text-white">
                <div className="max-w-4xl mx-auto text-center">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                    >
                        <Shield className="h-12 w-12 mx-auto mb-6 opacity-90" />
                        <h2 className="text-3xl md:text-4xl font-bold mb-6 font-heading">
                            Transparency & Trust
                        </h2>
                        <p className="text-lg md:text-xl opacity-90 max-w-2xl mx-auto mb-8 leading-relaxed">
                            Every answer provided by the Knowledge Hub includes direct citations to the source documents.
                            We believe in transparency—you should always be able to verify the information
                            and dive deeper into the original research.
                        </p>
                        <Link href="/">
                            <Button size="lg" className="bg-white text-[#692080] hover:bg-slate-100 text-lg px-8 border-none">
                                Start Exploring
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </Link>
                    </motion.div>
                </div>
            </section>

            {/* Contact Section */}
            <section className="py-20 px-4">
                <div className="max-w-2xl mx-auto text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                    >
                        <Mail className="h-10 w-10 mx-auto mb-6 text-[#692080] dark:text-purple-400" />
                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
                            Have Questions?
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-8">
                            We'd love to hear from you. Reach out to learn more about the Knowledge Hub.
                        </p>
                        <Button variant="outline" className="dark:border-slate-600 dark:text-slate-300">
                            <Mail className="mr-2 h-4 w-4" />
                            Contact Us
                        </Button>
                    </motion.div>
                </div>
            </section>
        </div>
    );
}
