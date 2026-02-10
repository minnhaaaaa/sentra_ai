"""
Example usage of the SentimentAnalyzer class.
This demonstrates how to use the sentiment analysis logic directly.
"""

from app.models.sentiment_analyzer import SentimentAnalyzer


def main():
    # Initialize the sentiment analyzer
    print("Initializing SentimentAnalyzer...")
    analyzer = SentimentAnalyzer()
    
    # Example 1: Single text analysis
    print("\n--- Single Text Analysis ---")
    test_texts = [
        "I absolutely love this product! It's amazing.",
        "This is terrible and I hate it.",
        "The service was okay, nothing special.",
    ]
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"Sentiment: {result['sentiment'].upper()}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Positive Score: {result['positive_score']:.4f}")
        print(f"Negative Score: {result['negative_score']:.4f}")
    
    # Example 2: Batch analysis
    print("\n\n--- Batch Analysis ---")
    batch_texts = [
        "This is wonderful!",
        "I'm very disappointed.",
        "It's fine."
    ]
    
    batch_results = analyzer.batch_analyze(batch_texts)
    for i, result in enumerate(batch_results, 1):
        print(f"\nText {i}: {result['text']}")
        print(f"Sentiment: {result['sentiment'].upper()} ({result['confidence']:.2%})")


if __name__ == "__main__":
    main()
