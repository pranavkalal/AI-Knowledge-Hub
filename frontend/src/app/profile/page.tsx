"use client";

import { useState, useEffect } from "react";
import { User, Mail, MapPin, Briefcase, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { PersonaType } from "@/lib/api";

export default function ProfilePage() {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [location, setLocation] = useState("");
    const [defaultPersona, setDefaultPersona] = useState<PersonaType>("grower");

    useEffect(() => {
        // Load saved profile from localStorage
        const savedProfile = localStorage.getItem("user_profile");
        if (savedProfile) {
            const profile = JSON.parse(savedProfile);
            setName(profile.name || "");
            setEmail(profile.email || "");
            setLocation(profile.location || "");
            setDefaultPersona(profile.defaultPersona || "grower");
        }
    }, []);

    const handleSave = () => {
        const profile = { name, email, location, defaultPersona };
        localStorage.setItem("user_profile", JSON.stringify(profile));
        toast.success("Profile saved successfully");
    };

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
        <div className="min-h-screen bg-background p-8">
            <div className="max-w-3xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3 font-heading">
                        <User className="h-8 w-8 text-purple-600" />
                        Profile
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Manage your personal information and preferences
                    </p>
                </motion.div>

                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="space-y-6"
                >
                    {/* Avatar Section */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700">
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-6">
                                    <div className="h-24 w-24 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-3xl font-bold">
                                        {name ? name.charAt(0).toUpperCase() : "U"}
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-semibold dark:text-white">
                                            {name || "Your Name"}
                                        </h2>
                                        <p className="text-slate-500 dark:text-slate-400">
                                            {email || "your.email@example.com"}
                                        </p>
                                        <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
                                            {location || "Location not set"}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Personal Information */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700">
                            <CardHeader>
                                <CardTitle className="dark:text-white">Personal Information</CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Update your personal details
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                        <User className="h-4 w-4" /> Name
                                    </label>
                                    <Input
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        placeholder="Enter your name"
                                        className="dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                        <Mail className="h-4 w-4" /> Email
                                    </label>
                                    <Input
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="Enter your email"
                                        type="email"
                                        className="dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                        <MapPin className="h-4 w-4" /> Location
                                    </label>
                                    <Input
                                        value={location}
                                        onChange={(e) => setLocation(e.target.value)}
                                        placeholder="e.g., Brisbane, QLD"
                                        className="dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Default Persona */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 dark:text-white">
                                    <Briefcase className="h-5 w-5" />
                                    Default Persona
                                </CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Choose your default persona for search queries
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-3">
                                    <Button
                                        variant={defaultPersona === "grower" ? "default" : "outline"}
                                        onClick={() => setDefaultPersona("grower")}
                                        className="h-auto py-4 flex flex-col gap-2"
                                    >
                                        <span className="text-2xl">🌱</span>
                                        <span>Grower</span>
                                    </Button>
                                    <Button
                                        variant={defaultPersona === "researcher" ? "default" : "outline"}
                                        onClick={() => setDefaultPersona("researcher")}
                                        className="h-auto py-4 flex flex-col gap-2"
                                    >
                                        <span className="text-2xl">🔬</span>
                                        <span>Researcher</span>
                                    </Button>
                                    <Button
                                        variant={defaultPersona === "extension_officer" ? "default" : "outline"}
                                        onClick={() => setDefaultPersona("extension_officer")}
                                        className="h-auto py-4 flex flex-col gap-2"
                                    >
                                        <span className="text-2xl">📋</span>
                                        <span>Extension</span>
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Save Button */}
                    <motion.div variants={item}>
                        <Button
                            onClick={handleSave}
                            className="w-full h-12 text-lg bg-purple-600 hover:bg-purple-700"
                        >
                            <Save className="h-5 w-5 mr-2" />
                            Save Profile
                        </Button>
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
}

