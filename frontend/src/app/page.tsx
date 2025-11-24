"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, ArrowRight, Leaf, Droplets, Sprout } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/chat?q=${encodeURIComponent(query)}`);
    }
  };

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-slate-50 px-4">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="w-full max-w-3xl space-y-8 text-center"
      >
        <motion.div variants={item} className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl text-slate-900">
            Unlock <span className="text-[#692080]">Cotton Research</span>
          </h1>
          <p className="mx-auto max-w-[700px] text-slate-500 md:text-xl">
            Ask complex questions about Australian cotton R&D. Get answers grounded in
            verified reports, with direct citations to the source PDF.
          </p>
        </motion.div>

        <motion.div variants={item} className="mx-auto w-full max-w-2xl">
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-4 top-3.5 h-5 w-5 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about yield trends, pest management, or water efficiency..."
              className="h-12 w-full rounded-full border-slate-200 bg-white pl-12 pr-4 shadow-sm transition-all focus:border-[#692080] focus:ring-[#692080]"
            />
            <Button
              type="submit"
              size="icon"
              className="absolute right-1.5 top-1.5 h-9 w-9 rounded-full bg-[#692080] hover:bg-[#501860]"
            >
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>
        </motion.div>

        <motion.div variants={item} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            {
              icon: Leaf,
              text: "What are the best practices for integrated pest management?",
              color: "text-purple-600",
              bg: "bg-purple-50",
            },
            {
              icon: Droplets,
              text: "Explain the nitrogen use efficiency guidelines for 2024.",
              color: "text-blue-600",
              bg: "bg-blue-50",
            },
            {
              icon: Sprout,
              text: "How does soil moisture affect cotton yield potential?",
              color: "text-amber-600",
              bg: "bg-amber-50",
            },
          ].map((card, i) => (
            <div
              key={i}
              onClick={() => setQuery(card.text)}
              className="group relative flex cursor-pointer flex-col items-start rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-all hover:border-[#692080]/50 hover:shadow-md"
            >
              <div className={`mb-3 rounded-lg ${card.bg} p-2 ${card.color}`}>
                <card.icon className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium text-slate-700 group-hover:text-[#692080]">
                {card.text}
              </p>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
