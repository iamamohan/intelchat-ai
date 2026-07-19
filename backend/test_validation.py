"""
Quick test to simulate what validate_answer_keywords does with the old vs new stop_words.
"""
import re

# === OLD (buggy) stop_words ===
old_stop_words = {
    "what", "is", "are", "the", "a", "an", "of", "to", "in", "for", "with",
    "on", "at", "by", "about", "how", "why", "where", "who", "define",
    "explain", "describe", "meaning", "definition", "question", "would",
    "should", "could", "from", "this", "that", "these", "those", "their",
    "them", "then", "there", "they", "been", "have", "were", "will", "your",
    "couldn't", "cannot", "find", "sufficient", "information", "uploaded",
    "documents", "answer", "however", "under", "about", "other", "their",
    "there", "thereby", "therefore", "here", "about", "above", "would",
    "outlined", "below", "following", "table", "comparison", "compare",
    "difference", "differences", "different", "distinguish", "summary",
    "summarize", "explained", "described", "provides", "features", "feature",
    "details", "detailed", "various", "multiple", "several", "aspects",
    "characteristics", "advantages", "disadvantages", "benefits", "drawbacks",
    "public", "private", "hybrid", "cloud", "computing"
}

# === NEW (fixed) stop_words ===
new_stop_words = {
    "what", "is", "are", "the", "a", "an", "of", "to", "in", "for", "with",
    "on", "at", "by", "about", "how", "why", "where", "who", "would",
    "should", "could", "from", "this", "that", "these", "those",
    "them", "then", "there", "they", "been", "have", "were", "will", "your",
    "cannot", "however", "under", "other", "thereby", "therefore",
    "here", "above", "below", "following", "also", "which", "their",
    "when", "than", "more", "some", "such", "into", "over", "after"
}

# A sample LLM-generated answer about cloud computing
sample_answer = """
Cloud computing is a model for delivering computing services including servers, storage, 
databases, networking, software, analytics, and intelligence over the internet (the cloud). 
It offers advantages such as scalability, cost savings, and flexibility. Public cloud providers 
like AWS and Azure provide infrastructure as a service. Private clouds offer dedicated resources 
while hybrid clouds combine both approaches.
"""

# Sample context from ChromaDB
sample_context = """
Cloud computing refers to the delivery of computing services over the internet. 
Private Cloud Software includes Eucalyptus, Open Nebula, Open Stack.
The cloud environment provides advantages including scalability and cost reduction.
Public and hybrid cloud models are widely adopted in enterprise computing.
"""

question = "What are the advantages of cloud computing?"

def check(stop_words, label):
    answer_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', sample_answer.lower()))
    answer_keywords = {w for w in answer_words if w not in stop_words}

    context_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', sample_context.lower()))
    context_keywords = {w for w in context_words if w not in stop_words}

    question_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', question.lower()))
    question_keywords = {w for w in question_words if w not in stop_words}

    allowed = context_keywords | question_keywords
    matched = answer_keywords & allowed
    ratio = len(matched) / len(answer_keywords) if answer_keywords else 1.0

    print(f"\n=== {label} ===")
    print(f"  Answer keywords ({len(answer_keywords)}): {sorted(answer_keywords)}")
    print(f"  Allowed keywords ({len(allowed)}): {sorted(list(allowed))[:20]}...")
    print(f"  Matched ({len(matched)}): {sorted(matched)}")
    print(f"  Match ratio: {ratio:.2f}")
    print(f"  OLD threshold (0.30): {'PASS' if ratio >= 0.30 else 'FAIL -> returns fallback!'}")
    print(f"  NEW threshold (0.15): {'PASS' if ratio >= 0.15 else 'FAIL -> returns fallback!'}")

check(old_stop_words, "OLD stop_words (BUGGY)")
check(new_stop_words, "NEW stop_words (FIXED)")
