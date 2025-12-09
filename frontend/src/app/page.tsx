"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, ArrowRight, Leaf, Droplets, Sprout, Users, FlaskConical, BookOpen, Bug, Microscope, FileText, Tractor, Beaker, ClipboardList } from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { PersonaType } from "@/lib/api";

// Persona-specific configurations
const personaConfig = {
  grower: {
    placeholder: "How do I manage pests on my farm?",
    cards: [
      {
        icon: Bug,
        text: "What are the best ways to control silverleaf whitefly?",
        color: "text-purple-600",
        bg: "bg-purple-50",
      },
      {
        icon: Droplets,
        text: "How can I improve water efficiency in my irrigation?",
        color: "text-blue-600",
        bg: "bg-blue-50",
      },
      {
        icon: Tractor,
        text: "What soil management practices improve cotton yield?",
        color: "text-amber-600",
        bg: "bg-amber-50",
      },
    ],
  },
  researcher: {
    placeholder: "What does the latest research say about...?",
    cards: [
      {
        icon: Microscope,
        text: "What are the mechanisms of disease suppression in cotton soils?",
        color: "text-purple-600",
        bg: "bg-purple-50",
      },
      {
        icon: Beaker,
        text: "How does dissolved organic nitrogen affect nutrient cycling?",
        color: "text-blue-600",
        bg: "bg-blue-50",
      },
      {
        icon: FlaskConical,
        text: "What are the latest findings on insect resistance monitoring?",
        color: "text-amber-600",
        bg: "bg-amber-50",
      },
    ],
  },
  extension_officer: {
    placeholder: "What guidance can I share with growers about...?",
    cards: [
      {
        icon: ClipboardList,
        text: "What are the key IPM recommendations for this season?",
        color: "text-purple-600",
        bg: "bg-purple-50",
      },
      {
        icon: BookOpen,
        text: "How should growers approach nitrogen management?",
        color: "text-blue-600",
        bg: "bg-blue-50",
      },
      {
        icon: FileText,
        text: "What are the best practices for weed management in cotton?",
        color: "text-amber-600",
        bg: "bg-amber-50",
      },
    ],
  },
};

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [persona, setPersona] = useState<PersonaType>("grower");

  const currentConfig = useMemo(() => personaConfig[persona], [persona]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/chat?q=${encodeURIComponent(query)}&persona=${persona}`);
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
                  placeholder={currentConfig.placeholder}
                  className="flex-1 border-none bg-transparent text-lg placeholder:text-slate-500 focus-visible:ring-0 focus-visible:ring-offset-0"
                />
                <div className="flex items-center space-x-2 text-slate-400">
                  <div className="relative">
                    <select
                      value={persona}
                      onChange={(e) => setPersona(e.target.value as PersonaType)}
                      className="appearance-none bg-white border border-slate-200 rounded-lg px-3 py-2 pr-8 text-sm text-slate-600 cursor-pointer hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                    >
                      <option value="grower">🌱 Grower</option>
                      <option value="researcher">🔬 Researcher</option>
                      <option value="extension_officer">📋 Extension</option>
                    </select>
                    <Users className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                  </div>
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

          <AnimatePresence mode="wait">
            <motion.div
              key={persona}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="grid grid-cols-1 gap-4 sm:grid-cols-3"
            >
              {currentConfig.cards.map((card, i) => (
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
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}
