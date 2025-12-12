"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, ArrowRight, Leaf, Droplets, Sprout } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

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
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col relative bg-white px-4">
      {/* Top Logo Area */}
      <div className="absolute top-4 left-4">
        <img src="/logo.png" alt="CRDC Logo" className="h-8 w-auto object-contain" />
      </div>

      <div className="flex flex-1 flex-col items-center justify-center">
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
            <form onSubmit={handleSearch} className="relative group">
              <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20 opacity-0 transition-opacity duration-500 group-hover:opacity-100 blur-xl" />
              <div className="relative flex items-center rounded-3xl bg-[#f0f4f9] px-4 py-3 shadow-sm transition-all focus-within:bg-white focus-within:shadow-md hover:bg-[#e2e7eb]">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask about pests, water efficiency, or yield data..."
                  className="flex-1 border-none bg-transparent text-lg placeholder:text-slate-500 focus-visible:ring-0 focus-visible:ring-offset-0"
                />
                <div className="flex items-center space-x-2 text-slate-400">
                  <Button
                    type="submit"
                    size="icon"
                    variant="ghost"
                    className={cn(
                      "h-10 w-10 rounded-full transition-all",
                      query.trim() ? "bg-[#692080] text-white hover:bg-[#501860]" : "hover:bg-slate-200"
                    )}
                  >
                    {query.trim() ? <ArrowRight className="h-5 w-5" /> : <Search className="h-5 w-5" />}
                  </Button>
                </div>
              </div>
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
                className="group relative flex cursor-pointer flex-col items-center justify-center rounded-xl bg-[#f0f4f9] p-4 text-center transition-all hover:bg-[#dde3ea]"
              >
                <div className="mb-3 rounded-full bg-white p-2 shadow-sm">
                  <card.icon className={`h-6 w-6 ${card.color}`} />
                </div>
                <p className="text-sm font-medium text-slate-700">
                  {card.text}
                </p>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
