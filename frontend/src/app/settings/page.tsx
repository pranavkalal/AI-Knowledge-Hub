"use client";

import { useState, useEffect } from "react";
import { Settings, Moon, Sun, Server, User, Bell, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTheme } from "next-themes";
import { motion } from "framer-motion";
import { toast } from "sonner";

export default function SettingsPage() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const [apiEndpoint, setApiEndpoint] = useState("http://127.0.0.1:8000/api");

    useEffect(() => {
        setMounted(true);
        const savedEndpoint = localStorage.getItem("api_endpoint");
        if (savedEndpoint) setApiEndpoint(savedEndpoint);
    }, []);

    const handleSaveEndpoint = () => {
        localStorage.setItem("api_endpoint", apiEndpoint);
        toast.success("API endpoint saved successfully");
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
                        <Settings className="h-8 w-8 text-purple-600" />
                        Settings
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Customize your Knowledge Hub experience
                    </p>
                </motion.div>

                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="space-y-6"
                >
                    {/* Appearance */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 dark:text-white">
                                    {mounted && theme === "dark" ? (
                                        <Moon className="h-5 w-5" />
                                    ) : (
                                        <Sun className="h-5 w-5" />
                                    )}
                                    Appearance
                                </CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Choose how the Knowledge Hub looks to you
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-3">
                                    <Button
                                        variant={mounted && theme === "light" ? "default" : "outline"}
                                        onClick={() => setTheme("light")}
                                        className="flex-1"
                                    >
                                        <Sun className="h-4 w-4 mr-2" />
                                        Light
                                    </Button>
                                    <Button
                                        variant={mounted && theme === "dark" ? "default" : "outline"}
                                        onClick={() => setTheme("dark")}
                                        className="flex-1"
                                    >
                                        <Moon className="h-4 w-4 mr-2" />
                                        Dark
                                    </Button>
                                    <Button
                                        variant={mounted && theme === "system" ? "default" : "outline"}
                                        onClick={() => setTheme("system")}
                                        className="flex-1"
                                    >
                                        <Settings className="h-4 w-4 mr-2" />
                                        System
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* API Configuration */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 dark:text-white">
                                    <Server className="h-5 w-5" />
                                    API Configuration
                                </CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Configure the backend API endpoint
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex gap-3">
                                    <Input
                                        value={apiEndpoint}
                                        onChange={(e) => setApiEndpoint(e.target.value)}
                                        placeholder="http://127.0.0.1:8000/api"
                                        className="flex-1 dark:bg-slate-700 dark:border-slate-600 dark:text-white"
                                    />
                                    <Button onClick={handleSaveEndpoint}>
                                        Save
                                    </Button>
                                </div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Changes will take effect on page reload
                                </p>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Notifications - Coming Soon */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700 opacity-60">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 dark:text-white">
                                    <Bell className="h-5 w-5" />
                                    Notifications
                                    <span className="ml-2 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 px-2 py-1 rounded-full">
                                        Coming Soon
                                    </span>
                                </CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Configure notification preferences
                                </CardDescription>
                            </CardHeader>
                        </Card>
                    </motion.div>

                    {/* Privacy - Coming Soon */}
                    <motion.div variants={item}>
                        <Card className="dark:bg-slate-800 dark:border-slate-700 opacity-60">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 dark:text-white">
                                    <Shield className="h-5 w-5" />
                                    Privacy & Data
                                    <span className="ml-2 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 px-2 py-1 rounded-full">
                                        Coming Soon
                                    </span>
                                </CardTitle>
                                <CardDescription className="dark:text-slate-400">
                                    Manage your data and privacy settings
                                </CardDescription>
                            </CardHeader>
                        </Card>
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
}

