/**
 * Next.js integration library for the PTE Scoring API.
 * Use this in your Next.js app to call the scoring API and use Vercel AI Gateway.
 */

"use client";

import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

const SCORING_API_URL = process.env.NEXT_PUBLIC_SCORING_API_URL || "http://localhost:8000";

/**
 * Client-side scoring interface.
 */
export async function scoreSubmission(
  text: string,
  options?: {
    useAI?: boolean;
    endpoint?: string;
    metadata?: Record<string, any>;
  }
): Promise<any> {
  const endpoint = options?.endpoint || `${SCORING_API_URL}/score`;

  const payload = {
    text,
    metadata: options?.metadata || {},
  };

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Scoring failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Score with AI agent integration (calls Vercel AI Gateway from client).
 */
export async function scoreWithAI(
  text: string,
  systemPrompt?: string
): Promise<any> {
  const systemInstruction =
    systemPrompt ||
    `You are a PTE Academic scoring expert. Analyze the following text and provide scores for:
- Fluency (0-100): lexical diversity, sentence complexity, discourse markers
- Lexical Resource (0-100): vocabulary range, academic word use
- Grammar (0-100): grammatical accuracy and sentence construction
- Communicative (0-100): how effectively the text conveys meaning
- Pronunciation Proxy (0-100): based on text phonetic complexity

Respond with a valid JSON object:
{
  "fluency": <number>,
  "lexical_resource": <number>,
  "grammar": <number>,
  "communicative": <number>,
  "pronunciation": <number>,
  "rationale": "Brief explanation"
}`;

  const prompt = `${systemInstruction}\n\nText to score:\n${text}`;

  const result = await generateText({
    model: openai("gpt-4-turbo"),
    prompt,
    temperature: 0.7,
  });

  try {
    return JSON.parse(result.text);
  } catch {
    return { raw_response: result.text };
  }
}

/**
 * Stream scoring updates via Server-Sent Events.
 */
export function subscribeToScoringUpdates(
  jobId: string,
  onUpdate: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(
    `${SCORING_API_URL}/stream/scoring/${jobId}`
  );

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onUpdate(data);
    } catch (e) {
      onError?.(new Error(`Failed to parse event: ${e}`));
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    onError?.(new Error("EventSource connection closed"));
  };

  // Return unsubscribe function
  return () => eventSource.close();
}

/**
 * Create an assessment on the backend.
 */
export async function createAssessment(
  studentId: string,
  metadata?: Record<string, any>
): Promise<any> {
  const response = await fetch(`${SCORING_API_URL}/assessments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_id: studentId,
      metadata,
    }),
  });

  if (!response.ok) {
    throw new Error(`Assessment creation failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get assessment details.
 */
export async function getAssessment(assessmentId: string): Promise<any> {
  const response = await fetch(`${SCORING_API_URL}/assessments/${assessmentId}`);

  if (!response.ok) {
    throw new Error(`Get assessment failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a background scoring job.
 */
export async function createScoringJob(
  text: string,
  metadata?: Record<string, any>
): Promise<any> {
  const response = await fetch(`${SCORING_API_URL}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      metadata,
    }),
  });

  if (!response.ok) {
    throw new Error(`Job creation failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Poll job status.
 */
export async function getJobStatus(jobId: string): Promise<any> {
  const response = await fetch(`${SCORING_API_URL}/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error(`Get job status failed: ${response.statusText}`);
  }

  return response.json();
}
