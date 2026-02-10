"use client"

import { useSearchParams, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { RetroGrid } from "@/components/ui/retro-grid"
import { SmoothCursor } from "@/components/ui/smooth-cursor"

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
  priority: "High" | "Medium" | "Low"
}

export default function ResultPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [ticketText, setTicketText] = useState("")
  const [results, setResults] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)

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
        
        // Determine sentiment label from API response
        const sentimentLabel = sentimentData.sentiment === "positive" ? "Positive" : 
                              sentimentData.sentiment === "negative" ? "Negative" : "Neutral"
        
        setResults({
          churnRisk: {
            probability: predictData.churn_probability ?? 0,
            label: predictData.churn_label ?? "Low",
          },
          sentiment: {
            score: sentimentData.positive_score,
            label: sentimentLabel,
          },
          category: predictData.category || "Unknown",
          priority: "High",
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
    if (priority === "High") return "text-red-400 bg-red-950"
    if (priority === "Medium") return "text-yellow-400 bg-yellow-950"
    return "text-green-400 bg-green-950"
  }

  return (
    <div className="w-full min-h-screen bg-black text-white overflow-hidden">
      <SmoothCursor />

      {/* Header */}
      <section className="relative w-full py-16 px-4 border-b border-gray-800">
        <RetroGrid angle={65} cellSize={60} opacity={0.1} />
        <div className="relative z-10 max-w-6xl mx-auto">
          <button
            onClick={() => router.push("/")}
            className="mb-8 px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors border border-gray-700 rounded-lg hover:border-gray-500"
          >
            ← Back to Home
          </button>
          <h1 className="text-5xl md:text-6xl font-bold mb-4">Analysis Results</h1>
          <p className="text-gray-400 max-w-2xl">
            Here are the AI insights for your customer support ticket
          </p>
        </div>
      </section>

      {/* Ticket Display */}
      <section className="w-full py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-semibold mb-6 text-gray-100">Your Ticket</h2>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
            <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">{ticketText}</p>
          </div>
        </div>
      </section>

      {/* Results Section */}
      <section className="w-full py-16 px-4">
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
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-blue-500/20">
                <div className="flex flex-col h-full">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Churn Prediction
                  </h3>
                  <div className="flex-1 flex flex-col justify-between">
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
                    <div>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getRiskColor(results.churnRisk.label)}`}>
                        {results.churnRisk.label} Risk
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sentiment Analysis Card */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-green-500/20">
                <div className="flex flex-col h-full">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Sentiment Analysis
                  </h3>
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <p className="text-gray-400 text-sm mb-3">Sentiment Score</p>
                      <p className="text-3xl font-bold text-green-400 mb-2">
                        {(results.sentiment.score * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getSentimentColor(results.sentiment.label)}`}>
                        {results.sentiment.label}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI Insights Card */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-purple-500/20">
                <div className="flex flex-col h-full">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Category
                  </h3>
                  <div className="flex-1 flex flex-col justify-between">
                    <p className="text-gray-400 text-sm mb-3">Predicted Category</p>
                    <div>
                      <p className="text-2xl font-bold text-purple-400 mb-4">
                        {results.category}
                      </p>
                      <span className="px-3 py-1 rounded-full text-sm font-semibold text-purple-400 bg-purple-950">
                        Classification
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Priority Card */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 hover:border-gray-700 transition-all hover:shadow-lg hover:shadow-orange-500/20">
                <div className="flex flex-col h-full">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Priority
                  </h3>
                  <div className="flex-1 flex flex-col justify-between">
                    <p className="text-gray-400 text-sm mb-3">Recommended Priority</p>
                    <div>
                      <p className="text-2xl font-bold text-orange-400 mb-4">
                        {results.priority}
                      </p>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getPriorityColor(results.priority)}`}>
                        {results.priority} Priority
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      {/* Action Section */}
      <section className="w-full py-16 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-2xl font-semibold mb-6 text-gray-100">What would you like to do next?</h2>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => router.push("/")}
              className="px-8 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 transition-all text-white font-semibold"
            >
              Analyze Another Ticket
            </button>
            <button
              onClick={() => {
                const text = encodeURIComponent(ticketText)
                // Can integrate with actual backend API here
                alert("Export feature coming soon!")
              }}
              className="px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 transition-all text-gray-300 hover:text-white font-semibold"
            >
              Export Results
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <section className="w-full py-12 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-gray-500">© 2026 Sentra AI. All rights reserved.</p>
        </div>
      </section>
    </div>
  )
}
