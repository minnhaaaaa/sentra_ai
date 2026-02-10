"use client"

import { useSearchParams, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { SmoothCursor } from "@/components/ui/smooth-cursor" // SmoothCursor for cool cursor effect
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card" // Shadcn Card
import { Badge } from "@/components/ui/badge" // Shadcn Badge

interface AnalysisResult {
  churnRisk: {
    probability: number
    label: "High" | "Medium" | "Low"
  }
  sentiment: {
    score: number
    label: "Positive" | "Neutral" | "Negative"
  }
  category: string
  priority: string
  priorityScore?: number
}

export default function ResultPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [ticketText, setTicketText] = useState("")
  const [results, setResults] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [showHero, setShowHero] = useState(true) // Control whether hero is in DOM at all

  useEffect(() => {
    const ticket = searchParams.get("ticket")
    if (!ticket) {
      router.push("/")
      return
    }
    setTicketText(ticket)
    // Call backend APIs to get category classification and sentiment analysis
    ;(async () => {
      try {
        const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000")
        
        // Make both API calls in parallel
        const [predictResp, sentimentResp] = await Promise.all([
          fetch(`${API_URL}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: ticket }),
          }),
          fetch(`${API_URL}/sentiment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: ticket }),
          })
        ])
        
        if (!predictResp.ok) throw new Error(`Predict API error ${predictResp.status}`)
        if (!sentimentResp.ok) throw new Error(`Sentiment API error ${sentimentResp.status}`)
        
        const predictData = await predictResp.json()
        const sentimentData = await sentimentResp.json()
        
        // Prefer sentiment coming from predict if available (keeps UI consistent with priority)
        const sentimentLabelFromPredict = predictData.sentiment_label
        const sentimentScoreFromPredict = predictData.sentiment_score
        const sentimentLabel = sentimentLabelFromPredict ? (sentimentLabelFromPredict === "positive" ? "Positive" : (sentimentLabelFromPredict === "negative" ? "Negative" : "Neutral")) : (sentimentData.sentiment === "positive" ? "Positive" : (sentimentData.sentiment === "negative" ? "Negative" : "Neutral"))
        const sentimentScore = sentimentScoreFromPredict ?? sentimentData.positive_score

        setResults({
          churnRisk: {
            probability: predictData.churn_probability ?? 0,
            label: predictData.churn_label ?? "Low",
          },
          sentiment: {
            score: sentimentScore,
            label: sentimentLabel,
          },
          category: predictData.category || "Unknown",
          priority: predictData.priority || "P4 – Low",
          priorityScore: predictData.priority_score ?? 0,
        })
      } catch (err) {
        console.error("API error:", err)
        setResults({
          churnRisk: {
            probability: 0.0,
            label: "Low",
          },
          sentiment: {
            score: 0.5,
            label: "Neutral",
          },
          category: "Unknown",
          priority: "Medium",
        })
      } finally {
        setLoading(false)
      }
    })()
  }, [searchParams, router])

  // Remove hero from DOM completely after animation finishes
  useEffect(() => {
    const timer = setTimeout(() => setShowHero(false), 3000) // 2s display + 1s fade
    return () => clearTimeout(timer)
  }, [])

  const getRiskColor = (label: string) => {
    if (label === "High") return "text-red-400 bg-red-950"
    if (label === "Medium") return "text-yellow-400 bg-yellow-950"
    return "text-green-400 bg-green-950"
  }

  const getSentimentColor = (label: string) => {
    if (label === "Positive") return "text-green-400 bg-green-950"
    if (label === "Negative") return "text-red-400 bg-red-950"
    return "text-blue-400 bg-blue-950"
  }

  const getPriorityColor = (priority: string) => {
    if (priority.startsWith("P1")) return "text-red-400 bg-red-950"
    if (priority.startsWith("P2")) return "text-orange-400 bg-orange-950"
    if (priority.startsWith("P3")) return "text-yellow-400 bg-yellow-950"
    return "text-green-400 bg-green-950"
  }

  return (
    <div className="w-full min-h-screen bg-black text-white overflow-hidden relative">
      <SmoothCursor /> {/* SmoothCursor for cool cursor effect */}

      {/* Subtle Grid Background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:50px_50px]"></div>

      {/* Hero Animation Overlay - Completely removed from DOM after animation */}
      {showHero && (
        <div className="fixed inset-0 bg-black flex items-center justify-center z-50 pointer-events-none animate-in fade-out-0 duration-1000 delay-2000">
          <h1 className="text-6xl md:text-8xl font-bold text-white animate-in zoom-in-50 duration-1000">
            Analysis Results
          </h1>
        </div>
      )}

      {/* Main Content - Always visible and clickable */}
      <div className="relative z-10">
        {/* Minimalistic Header */}
        <section className="relative w-full py-20 px-4 border-b border-gray-800 bg-black animate-in fade-in-0 slide-in-from-top-4 duration-500 delay-200">
          <div className="relative z-10 max-w-4xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Analysis Results
            </h1>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              Here are the AI insights for your customer support ticket
            </p>
          </div>
        </section>

        {/* Ticket Display */}
        <section className="w-full py-16 px-4 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-400">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-semibold mb-6 text-gray-100">Your Ticket</h2>
            <Card className="bg-gray-900 border border-gray-800">
              <CardContent className="p-8">
                <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">{ticketText}</p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Results Section */}
        <section className="w-full py-16 px-4 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-600">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-semibold mb-8 text-gray-100">Predictions</h2>

            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
                  <p className="text-gray-400">Analyzing your ticket...</p>
                </div>
              </div>
            ) : results ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Churn Prediction Card */}
                <Card className="bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-blue-500/20 hover:scale-105 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-800">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-gray-100">
                      Churn Prediction
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col justify-between h-full">
                    <div>
                      <div className="mb-4">
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all"
                            style={{ width: `${results.churnRisk.probability * 100}%` }}
                          ></div>
                        </div>
                      </div>
                      <p className="text-3xl font-bold text-blue-400 mb-2">
                        {(results.churnRisk.probability * 100).toFixed(0)}%
                      </p>
                    </div>
                    <Badge className={`${getRiskColor(results.churnRisk.label)}`}>
                      {results.churnRisk.label} Risk
                    </Badge>
                  </CardContent>
                </Card>

                {/* Sentiment Analysis Card */}
                <Card className="bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-green-500/20 hover:scale-105 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-1000">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-gray-100">
                      Sentiment Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col justify-between h-full">
                    <div>
                      <p className="text-gray-400 text-sm mb-3">Sentiment Score</p>
                      <p className="text-3xl font-bold text-green-400 mb-2">
                        {(results.sentiment.score * 100).toFixed(0)}%
                      </p>
                    </div>
                    <Badge className={`${getSentimentColor(results.sentiment.label)}`}>
                      {results.sentiment.label}
                    </Badge>
                  </CardContent>
                </Card>

                {/* AI Insights Card */}
                <Card className="bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-purple-500/20 hover:scale-105 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-1200">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-gray-100">
                      Category
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col justify-between h-full">
                    <p className="text-gray-400 text-sm mb-3">Predicted Category</p>
                    <div>
                      <p className="text-2xl font-bold text-purple-400 mb-4">
                        {results.category}
                      </p>
                      <Badge className="text-purple-400 bg-purple-950">
                        Classification
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Priority Card */}
                <Card className="bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-orange-500/20 hover:scale-105 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-1400">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-gray-100">
                      Priority
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col justify-between h-full">
                    <p className="text-gray-400 text-sm mb-3">Recommended Priority</p>
                    <div>
                      <p className="text-2xl font-bold text-orange-400 mb-4">
                        {results.priority}
                      </p>
                      <Badge className={`${getPriorityColor(results.priority)}`}>
                        {results.priority} Priority
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : null}
          </div>
        </section>

        {/* Action Section */}
        <section className="w-full py-16 px-4 border-t border-gray-800 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-1600">
          <div className="max-w-6xl mx-auto text-center">
            <h2 className="text-2xl font-semibold mb-6 text-gray-100">What would you like to do next?</h2>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => router.push("/")}
                className="relative z-20 px-8 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 transition-all text-white font-semibold cursor-pointer"
              >
                Analyze Another Ticket
              </button>
              <button
                onClick={() => {
                  const text = encodeURIComponent(ticketText)
                  // Can integrate with actual backend API here
                  alert("Export feature coming soon!")
                }}
                className="relative z-20 px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 transition-all text-gray-300 hover:text-white font-semibold cursor-pointer"
              >
                Export Results
              </button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <section className="w-full py-12 px-4 border-t border-gray-800 animate-in fade-in-0 slide-in-from-bottom-4 duration-500 delay-1800">
          <div className="max-w-6xl mx-auto text-center">
            <p className="text-gray-500">© 2026 Sentra AI. All rights reserved.</p>
          </div>
        </section>
      </div>
    </div>
  )
}