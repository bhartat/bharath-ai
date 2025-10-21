// frontend/src/app/page.tsx (FINAL)
'use client';
import React from 'react';
import { motion } from 'framer-motion';
import { FiZap, FiEdit, FiClock, FiShield } from 'react-icons/fi';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.2 } },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 100 } },
};

export default function LandingPage() {
  const googleLoginUrl = "http://127.0.0.1:8000/auth/google";

  return (
    <div className="min-h-screen w-full bg-slate-900 text-white font-sans">
      <div className="absolute inset-0 -z-10 h-full w-full bg-slate-900 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:14px_24px]">
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-blue-400 opacity-20 blur-[100px]"></div>
      </div>
      <header className="fixed top-0 left-0 right-0 z-20 bg-slate-900/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">bharath.ai</div>
          <a href={googleLoginUrl} className="px-4 py-2 text-sm font-medium rounded-md bg-white text-slate-900 hover:bg-gray-200 transition-colors">Sign In</a>
        </div>
      </header>
      <main className="container mx-auto px-6 flex flex-col items-center justify-center min-h-screen pt-24 text-center">
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="flex flex-col items-center">
          <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl font-extrabold tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-400">Achieve Inbox Zero.<br />Powered by AI.</motion.h1>
          <motion.p variants={itemVariants} className="mt-6 max-w-2xl text-lg text-gray-400">bharath.ai analyzes your emails, extracts action items, and drafts perfect replies, so you can focus on what matters.</motion.p>
          <motion.div variants={itemVariants} className="mt-8">
            <a href={googleLoginUrl} className="inline-flex items-center justify-center px-8 py-4 border border-transparent text-lg font-semibold rounded-full text-slate-900 bg-white hover:bg-gray-200 transition-transform transform hover:scale-105 shadow-lg">
              <svg className="w-6 h-6 mr-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512"><path fill="#4285F4" d="M488 261.8C488 403.3 381.5 512 244 512 109.8 512 0 402.2 0 261.8 0 122.4 109.8 13.5 244 13.5c73.5 0 134.3 29.1 175.9 76.2l-64.8 64.2c-23.4-22.3-55.4-35.8-91.1-35.8-70.1 0-128.2 57.2-128.2 128.2s58.1 128.2 128.2 128.2c80.3 0 114-52.7 118.8-78.2H244v-81.6h236.8c2.4 13.1 3.2 27.5 3.2 42.6z"/></svg>
              Get Started with Google
            </a>
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
}
