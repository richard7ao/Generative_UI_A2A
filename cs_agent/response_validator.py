"""Response validation and self-correction for CS agent.

Based on Advanced Strategy #11: Semantic Response Validation
Ensures agent responses actually answer the user's question.
"""

import os
from typing import Tuple

from google import genai
from google.genai import types

MODEL = os.environ.get("MODEL", "gemini-3.5-flash")


def _get_genai_client():
    """Get or create genai client."""
    return genai.Client()


async def validate_response(question: str, proposed_answer: str, search_results: list) -> Tuple[bool, str]:
    """Validate that the proposed answer actually addresses the question.
    
    Uses LLM-as-judge pattern to verify:
    1. Answer directly addresses the question
    2. Answer is supported by search results (no hallucination)
    3. No contradictions with known facts
    
    Args:
        question: Original user question
        proposed_answer: The answer the agent is about to send
        search_results: Results from KB search that informed the answer
        
    Returns:
        Tuple of (is_valid, corrected_answer_or_reason)
    """
    # Skip validation for very short answers
    if len(proposed_answer) < 50:
        return True, proposed_answer
    
    # Build validation prompt
    search_context = "\n".join([
        f"- {doc.get('title', 'Untitled')}: {doc.get('content', '')[:200]}"
        for doc in search_results[:3]
    ]) if search_results else "No search results available."
    
    validation_prompt = f"""You are a quality assurance validator for a customer service agent.

ORIGINAL QUESTION:
{question}

PROPOSED ANSWER:
{proposed_answer}

SEARCH RESULTS THAT INFORMED THE ANSWER:
{search_context}

VALIDATION CRITERIA:
1. Does the answer directly address the question? (Not just related, but actually answers it)
2. Is the answer fully supported by the search results? (No invented facts)
3. Are there any contradictions in the answer?
4. Is the tone appropriate for customer service? (Professional, helpful, not overly verbose)

RESPOND IN THIS FORMAT:
STATUS: VALID or INVALID
REASON: Brief explanation of why it's valid or what needs fixing
CORRECTED_ANSWER: If INVALID, provide the corrected answer. If VALID, say "N/A"

Example 1:
STATUS: VALID
REASON: Answer directly addresses the balance inquiry with accurate information
CORRECTED_ANSWER: N/A

Example 2:
STATUS: INVALID
REASON: Answer mentions a fee that wasn't in the search results
CORRECTED_ANSWER: Your current balance is $1,234.56. No additional fees apply.

Now validate:"""

    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=validation_prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        validation_text = response.text.strip()
        
        # Parse validation response
        is_valid = "STATUS: VALID" in validation_text or "STATUS:VALID" in validation_text
        
        # Extract corrected answer if provided
        corrected_answer = proposed_answer
        if "CORRECTED_ANSWER:" in validation_text:
            parts = validation_text.split("CORRECTED_ANSWER:")
            if len(parts) > 1:
                corrected = parts[1].strip()
                if corrected and corrected != "N/A":
                    corrected_answer = corrected
        
        return is_valid, corrected_answer
        
    except Exception as e:
        # On validation failure, return original answer
        print(f"[Response Validator] Validation error: {e}")
        return True, proposed_answer


async def self_correct(
    question: str,
    initial_answer: str,
    search_results: list,
    max_iterations: int = 2
) -> str:
    """Self-correction loop: validate and fix answer if needed.
    
    Args:
        question: Original question
        initial_answer: First draft answer
        search_results: Supporting evidence
        max_iterations: Max correction attempts
        
    Returns:
        Corrected answer
    """
    current_answer = initial_answer
    
    for iteration in range(max_iterations):
        is_valid, corrected = await validate_response(
            question, current_answer, search_results
        )
        
        if is_valid:
            if iteration > 0:
                print(f"[Self-Correction] Answer validated after {iteration + 1} iterations")
            return corrected
        
        # Use corrected version for next iteration
        current_answer = corrected
        print(f"[Self-Correction] Iteration {iteration + 1}: Answer corrected")
    
    # Return best effort after max iterations
    return current_answer


def should_validate(question: str, answer: str) -> bool:
    """Determine if validation is needed based on question/answer characteristics.
    
    Args:
        question: User question
        answer: Proposed answer
        
    Returns:
        True if validation should be performed
    """
    # Always validate complex answers
    if len(answer) > 300:
        return True
    
    # Always validate answers with numbers/facts
    if any(char.isdigit() for char in answer):
        return True
    
    # Validate if question is about specific facts
    fact_keywords = ["how much", "what is", "balance", "fee", "rate", "limit"]
    if any(kw in question.lower() for kw in fact_keywords):
        return True
    
    # Skip validation for simple acknowledgments
    if answer.strip().lower() in ["ok", "sure", "got it", "i understand"]:
        return False
    
    return True
