// SentraAI SaaS Tool
// This project is a customer support AI tool.
// Users can input ticket text and get predictions for churn, sentiment, category, and priority.
// The landing page should be visually engaging using Magic UI background animations and shadcn/ui components. This is a SaaS product, so the UI should look professional and modern.
// Copilot should assist in creating sections, forms, and layout for this SaaS tool.
// Use the logo in public folder for header. Make the header solid in color
// Change retro background to interactive grid pattern

"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { InteractiveGridPattern } from "@/components/ui/interactive-grid-pattern"
import { SmoothCursor } from "@/components/ui/smooth-cursor"


export default function Home() {
  const [ticketText, setTicketText] = useState("")
  const [displayedTitle, setDisplayedTitle] = useState("")
  const router = useRouter()
  const fullTitle = "SentraAI"

  useEffect(() => {
    let index = 0
    const interval = setInterval(() => {
      if (index < fullTitle.length) {
        setDisplayedTitle(fullTitle.substring(0, index + 1))
        index++
      } else {
        clearInterval(interval)
      }
    }, 100)
    return () => clearInterval(interval)
  }, [])

  const handleAnalyze = () => {
    if (ticketText.trim()) {
      router.push(`/result?ticket=${encodeURIComponent(ticketText)}`)
    }
  }

  return (
    <div className="w-full overflow-hidden bg-black">
      <SmoothCursor />

      {/* Header */}
      <header className="w-full h-20 flex items-center px-6 border-b border-gray-800 bg-black">
        <div className="flex items-center gap-3">
          <Image
            src="/logo.png"
            alt="SentraAI Logo"
            width={50}
            height={50}
            className="h-12 w-12 object-contain"
          />
          <span className="text-xl font-bold text-white">SentraAI</span>
        </div>
      </header>

      {/* Section 1: Hero */}
      <section className="relative w-full min-h-screen flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 w-full h-full">
          <InteractiveGridPattern
            className="w-full h-full opacity-30"
            dots="rgb(59, 130, 246)"
            lines="rgb(30, 80, 200)"
          />
        </div>
        <div className="relative z-10 flex flex-col items-center justify-center gap-8 px-4 text-center">
          <div className="h-20 flex items-center justify-center">
            <h1 className="text-6xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-blue-500 to-cyan-400 animate-shimmer min-h-20">
              {displayedTitle}
              {displayedTitle.length < fullTitle.length && (
                <span className="text-white animate-pulse ml-1">|</span>
              )}
            </h1>
          </div>
          <p className="max-w-2xl text-lg md:text-xl text-gray-400">
            Intelligent customer support analysis powered by advanced AI. Predict churn, analyze sentiment, and prioritize tickets automatically.
          </p>
        </div>
      </section>

      {/* Section 2: Ticket Input */}
      <section className="relative w-full py-20 px-4 bg-black border-t border-gray-800 overflow-hidden">
        <div className="absolute inset-0 w-full">
          <InteractiveGridPattern
            className="w-full h-full opacity-20"
            dots="rgb(59, 130, 246)"
            lines="rgb(30, 80, 200)"
          />
        </div>
        <div className="relative z-10 max-w-3xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-4 text-white">
            Analyze Your Ticket
          </h2>
          <p className="text-center text-gray-400 mb-12">
            Paste your customer support ticket below and let our AI provide insights.
          </p>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
            <div className="space-y-6">
              <div>
                <label htmlFor="ticket" className="block text-sm font-medium mb-2 text-white">
                  Support Ticket
                </label>
                <textarea
                  id="ticket"
                  value={ticketText}
                  onChange={(e) => setTicketText(e.target.value)}
                  placeholder="Paste your customer support ticket here..."
                  className="w-full h-32 p-4 border border-gray-700 rounded-lg bg-gray-800 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-all"
                />
              </div>

              <div className="flex justify-center">
                <button
                  onClick={handleAnalyze}
                  disabled={!ticketText.trim()}
                  className="group relative px-8 py-3 text-white font-semibold rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 overflow-hidden"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    Analyze Ticket
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      

      {/* Footer */}
      <section className="w-full py-12 px-4 bg-black border-t border-gray-800">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-gray-500">
            © 2026 Sentra AI. All rights reserved.
          </p>
        </div>
      </section>
    </div>
  )
}
