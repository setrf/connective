"use client";

import { signIn, useSession } from "next-auth/react";
import { redirect } from "next/navigation";
import { useEffect } from "react";
import { HeroCanvas } from "@/components/landing/hero-canvas";
import { WaveformCanvas } from "@/components/landing/waveform-canvas";
import { ScrambleText } from "@/components/landing/scramble-text";
import { FloatingNodes } from "@/components/landing/floating-nodes";
import { BracketCard } from "@/components/landing/bracket-card";

export default function Home() {
  const { data: session, status } = useSession();

  // Intersection observer for section dimming
  useEffect(() => {
    const sections = document.querySelectorAll(".section-container");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.remove("dimmed");
          } else {
            entry.target.classList.add("dimmed");
          }
        });
      },
      { threshold: 0.5 },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050505]">
        <div className="animate-pulse mono text-xs text-gray-500">
          INITIALIZING...
        </div>
      </div>
    );
  }

  if (session) {
    redirect("/dashboard");
  }

  const handleSignIn = () => signIn("google", { callbackUrl: "/dashboard" });

  return (
    <div className="landing-page bg-[#050505] text-[#EAEAEA] selection:bg-white selection:text-black">
      {/* ── Nav ── */}
      <nav className="fixed top-0 left-0 w-full z-50 px-6 py-6 flex justify-between items-center mix-blend-difference">
        <div className="flex items-center gap-4">
          <span className="mono text-xs text-white opacity-60">
            [ CONNECTIVE V.1.0 ]
          </span>
        </div>
        <div className="flex items-center gap-8">
          <span className="mono text-xs text-white opacity-60 hidden md:block">
            SYSTEM: SCANNING
          </span>
          <button onClick={handleSignIn} className="btn-primary">
            Get Started
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <header className="relative w-full h-screen flex flex-col justify-end p-6 md:p-12 overflow-hidden">
        <HeroCanvas />

        <div className="relative z-10 w-full max-w-7xl mx-auto mb-12 grid grid-cols-1 md:grid-cols-12 gap-8 items-end">
          <div
            className="md:col-span-8 fade-in-up"
            style={{ animationDelay: "0.2s" }}
          >
            <div className="mono text-xs text-gray-500 mb-4 flex items-center gap-2">
              <span>[ 00 ]</span>
              <div className="h-[1px] w-12 bg-gray-800" />
              <span>SIGNAL DETECTED</span>
            </div>
            <h1 className="hero-title text-white">
              Signal
              <br />
              in the overlap.
            </h1>
          </div>
          <div
            className="md:col-span-4 fade-in-up flex flex-col gap-6"
            style={{ animationDelay: "0.4s" }}
          >
            <p className="text-gray-400 text-lg leading-relaxed max-w-sm">
              Connective scans your Slack, GitHub, and Google Drive&mdash;then
              surfaces the hidden overlaps between teammates in real time.
            </p>
            <div className="mono text-xs text-gray-600">
              SCROLL TO CALIBRATE &darr;
            </div>
          </div>
        </div>

        {/* Corner decorations */}
        <div className="absolute top-6 left-6 w-4 h-4 border-t border-l border-white opacity-30" />
        <div className="absolute top-6 right-6 w-4 h-4 border-t border-r border-white opacity-30" />
        <div className="absolute bottom-6 left-6 w-4 h-4 border-b border-l border-white opacity-30" />
        <div className="absolute bottom-6 right-6 w-4 h-4 border-b border-r border-white opacity-30" />
      </header>

      {/* ── Main ── */}
      <main className="w-full relative z-10 bg-[#050505]">
        {/* Section 01 — Live Scanning */}
        <section className="min-h-[80vh] w-full flex items-center justify-center p-6 md:p-12 border-t border-[#1a1a1a]">
          <div className="w-full max-w-7xl grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-24 items-center group section-container">
            <div className="order-2 md:order-1">
              <div className="mono text-xs text-gray-500 mb-6 flex items-center gap-2">
                <span>[ 01 ]</span>
                <div className="h-[1px] w-8 bg-gray-800" />
                <span>LIVE SCANNING</span>
              </div>
              <h2 className="text-4xl md:text-5xl font-normal text-white mb-6 tracking-tight">
                Every channel,
                <br />
                every repo.
              </h2>
              <p className="text-gray-400 text-lg leading-relaxed mb-8 max-w-md">
                Connective watches your team&apos;s tools around the clock.
                Messages, commits, and documents are indexed as they
                happen&mdash;nothing slips through.
              </p>
              <ul className="mono text-xs text-gray-500 space-y-2 border-l border-gray-800 pl-4">
                <li className="flex justify-between w-48">
                  <span>SOURCES</span> <span>3</span>
                </li>
                <li className="flex justify-between w-48">
                  <span>LATENCY</span> <span>&lt;30s</span>
                </li>
                <li className="flex justify-between w-48">
                  <span>MODE</span> <span>ACTIVE</span>
                </li>
              </ul>
            </div>

            <BracketCard className="order-1 md:order-2">
              <WaveformCanvas />
              <div className="absolute bottom-4 left-4 mono text-[10px] text-gray-500">
                INPUT_SOURCE: SLACK_STREAM_01
              </div>
            </BracketCard>
          </div>
        </section>

        {/* Section 02 — Overlap Engine */}
        <section className="min-h-[80vh] w-full flex items-center justify-center p-6 md:p-12 border-t border-[#1a1a1a]">
          <div className="w-full max-w-7xl grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-24 items-center section-container group">
            <BracketCard>
              <FloatingNodes />
              <div className="absolute top-4 right-4 mono text-[10px] text-gray-500 text-right">
                STATUS: MAPPING
                <br />
                NODES: 4,021
              </div>
            </BracketCard>

            <div>
              <div className="mono text-xs text-gray-500 mb-6 flex items-center gap-2">
                <span>[ 02 ]</span>
                <div className="h-[1px] w-8 bg-gray-800" />
                <span>OVERLAP ENGINE</span>
              </div>
              <h2 className="text-4xl md:text-5xl font-normal text-white mb-6 tracking-tight">
                Collision
                <br />
                detection.
              </h2>
              <p className="text-gray-400 text-lg leading-relaxed mb-8 max-w-md">
                Connective maps who is working on what. When two people converge
                on the same problem without knowing, you&apos;ll see it
                instantly.
              </p>
            </div>
          </div>
        </section>

        {/* Section 03 — Synthesis */}
        <section className="min-h-[80vh] w-full flex items-center justify-center p-6 md:p-12 border-t border-[#1a1a1a]">
          <div className="w-full max-w-7xl grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-24 items-center section-container group">
            <div className="order-2 md:order-1">
              <div className="mono text-xs text-gray-500 mb-6 flex items-center gap-2">
                <span>[ 03 ]</span>
                <div className="h-[1px] w-8 bg-gray-800" />
                <span>SYNTHESIS</span>
              </div>
              <h2 className="text-4xl md:text-5xl font-normal text-white mb-6 tracking-tight">
                Cited answers.
              </h2>
              <p className="text-gray-400 text-lg leading-relaxed mb-8 max-w-md">
                Ask a question, get a sourced response. Every insight links back
                to the exact message, commit, or document it came from.
              </p>
              <button className="text-white border-b border-white pb-1 hover:opacity-70 transition-opacity mono text-xs tracking-widest uppercase">
                View Sample Output
              </button>
            </div>

            <BracketCard className="order-1 md:order-2">
              <div className="text-center">
                <ScrambleText />
                <div className="w-[1px] h-12 bg-white/20 mx-auto my-4" />
                <div className="mono text-[10px] text-gray-600">
                  RESOLVING...
                </div>
              </div>
            </BracketCard>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer className="w-full py-32 px-6 border-t border-[#1a1a1a] flex flex-col items-center justify-center text-center">
          <h2 className="text-5xl md:text-7xl font-medium text-white mb-12 tracking-tighter">
            Start connecting.
          </h2>
          <div className="flex flex-col items-center gap-6">
            <button onClick={handleSignIn} className="btn-primary scale-125">
              Sign In With Google
            </button>
            <span className="mono text-[10px] text-gray-600 uppercase mt-4">
              Slack &middot; GitHub &middot; Google Drive
              <br />
              Free during beta
            </span>
          </div>
          <div className="mt-24 mono text-[10px] text-gray-700 w-full max-w-7xl flex justify-between">
            <span>&copy; 2025 CONNECTIVE</span>
            <span>[ SYSTEM IDLE ]</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
