"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { api, AgentReply } from "@/lib/api";
import {
  FaBus,
  FaClock,
  FaCommentDots,
  FaExclamationTriangle,
  FaMapMarkerAlt,
  FaPaperPlane,
  FaRobot,
  FaRoute,
  FaSearch,
  FaTicketAlt,
} from "react-icons/fa";

type Message = {
  role: "user" | "assistant";
  text: string;
  meta?: Partial<AgentReply>;
};

const SUGGESTIONS = [
  "Which bus goes from Avadi to Koyambedu?",
  "How do I reach Siruseri IT Park?",
  "Show my latest ticket",
  "Track my booked bus",
  "How can I register a complaint?",
  "What is the cancellation policy?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text:
        "Hi! I’m BusMate, your Chennai MTC travel assistant. " +
        "I can help with route search, tickets, tracking, fares, " +
        "complaints, feedback, and journey guidance.",
    },
  ]);

  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<
    string | undefined
  >();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  const latestAssistantMeta = useMemo(() => {
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");

    return lastAssistantMessage?.meta;
  }, [messages]);

  async function submitMessage(text: string) {
    const cleanedText = text.trim();

    if (!cleanedText || loading) {
      return;
    }

    setInput("");
    setError("");

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "user",
        text: cleanedText,
      },
    ]);

    setLoading(true);

    try {
      const response = await api<AgentReply>(
        "/api/agents/chat",
        {
          method: "POST",
          body: JSON.stringify({
            message: cleanedText,
            session_id: sessionId,
          }),
        }
      );

      setSessionId(response.session_id);

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          text: response.reply,
          meta: response,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The assistant is temporarily unavailable."
      );

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          text:
            "I’m temporarily unable to connect to the AI service. " +
            "You can still search routes, book seats, view tickets, " +
            "and track buses using the main navigation.",
          meta: {
            agent: "Fallback Assistant",
            intent: "Out-of-Scope",
            ai_used: false,
            escalated: false,
          },
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function send(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();
    submitMessage(input);
  }

  function suggestionIcon(suggestion: string) {
    const lower = suggestion.toLowerCase();

    if (
      lower.includes("ticket") ||
      lower.includes("booked")
    ) {
      return <FaTicketAlt />;
    }

    if (
      lower.includes("track") ||
      lower.includes("reach")
    ) {
      return <FaMapMarkerAlt />;
    }

    if (
      lower.includes("complaint") ||
      lower.includes("policy")
    ) {
      return <FaExclamationTriangle />;
    }

    return <FaRoute />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-brand-700 to-brand-500 px-6 py-6 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 text-2xl">
                <FaRobot />
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/80">
                  AI-powered Chennai travel help
                </p>

                <h1 className="mt-1 text-2xl font-bold">
                  BusMate Assistant
                </h1>

                <p className="mt-1 text-sm text-white/80">
                  Ask about MTC routes, tickets, tracking,
                  fares, complaints, and policies.
                </p>
              </div>
            </div>

            <div className="rounded-full bg-white/15 px-4 py-2 text-sm font-semibold">
              {loading ? "Thinking..." : "Online"}
            </div>
          </div>
        </div>

        <div className="grid gap-6 p-5 lg:grid-cols-[1fr_280px]">
          <div className="flex min-h-[610px] flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-4">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`flex ${
                    message.role === "user"
                      ? "justify-end"
                      : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      message.role === "user"
                        ? "rounded-br-md bg-brand-600 text-white"
                        : "rounded-bl-md border border-slate-200 bg-white text-slate-800"
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-6">
                      {message.text}
                    </p>

                    {message.meta?.agent && (
                      <div
                        className={`mt-3 flex flex-wrap gap-2 border-t pt-2 text-[10px] ${
                          message.role === "user"
                            ? "border-white/20 text-white/75"
                            : "border-slate-100 text-slate-400"
                        }`}
                      >
                        <span>
                          Agent: {message.meta.agent}
                        </span>

                        <span>
                          Intent: {message.meta.intent}
                        </span>

                        <span>
                          {message.meta.ai_used
                            ? "AI response"
                            : "Rule fallback"}
                        </span>

                        {message.meta.escalated && (
                          <span>Escalated</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:120ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:240ms]" />
                      <span className="ml-1">
                        BusMate is preparing a response
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {error && (
              <p
                className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
                role="alert"
              >
                {error}
              </p>
            )}

            <form
              onSubmit={send}
              className="mt-4 flex gap-3"
            >
              <div className="relative flex-1">
                <FaCommentDots className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />

                <input
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  placeholder="Ask about an MTC route, fare, ticket, tracking, or complaint..."
                  value={input}
                  onChange={(event) =>
                    setInput(event.target.value)
                  }
                  disabled={loading}
                  aria-label="Message"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Send"
              >
                <FaPaperPlane />
              </button>
            </form>
          </div>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <h2 className="flex items-center gap-2 font-bold text-slate-900">
                <FaSearch className="text-brand-600" />
                Try asking
              </h2>

              <div className="mt-4 space-y-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    disabled={loading}
                    onClick={() =>
                      submitMessage(suggestion)
                    }
                    className="flex w-full items-start gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 text-left text-sm text-slate-700 transition hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50"
                  >
                    <span className="mt-0.5 text-brand-600">
                      {suggestionIcon(suggestion)}
                    </span>

                    <span>{suggestion}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
              <h2 className="flex items-center gap-2 font-bold text-blue-900">
                <FaBus />
                Quick actions
              </h2>

              <div className="mt-4 grid gap-2">
                <Link
                  href="/search"
                  className="flex items-center gap-3 rounded-xl bg-white px-3 py-3 text-sm font-semibold text-blue-800 shadow-sm"
                >
                  <FaRoute />
                  Search MTC buses
                </Link>

                <Link
                  href="/tickets"
                  className="flex items-center gap-3 rounded-xl bg-white px-3 py-3 text-sm font-semibold text-blue-800 shadow-sm"
                >
                  <FaTicketAlt />
                  View my tickets
                </Link>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4">
              <h2 className="font-bold text-slate-900">
                Assistant status
              </h2>

              <div className="mt-3 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">
                    Current mode
                  </span>

                  <span className="font-semibold text-slate-800">
                    {latestAssistantMeta?.ai_used
                      ? "AI"
                      : "Rules / fallback"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">
                    Agent
                  </span>

                  <span className="text-right font-semibold text-slate-800">
                    {latestAssistantMeta?.agent ??
                      "BusMate Assistant"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">
                    Intent
                  </span>

                  <span className="text-right font-semibold text-slate-800">
                    {latestAssistantMeta?.intent ??
                      "Greeting"}
                  </span>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="flex gap-3">
                <FaClock className="mt-1 shrink-0 text-amber-700" />

                <p className="text-sm leading-6 text-amber-900">
                  Route and ETA information in this project
                  is based on imported MTC route data and
                  simulated journey timing.
                </p>
              </div>
            </section>
          </aside>
        </div>
      </section>
    </div>
  );
}