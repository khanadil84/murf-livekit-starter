'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
}: WelcomeViewProps) => {
  const [starting, setStarting] = useState(false);

  const handleStart = () => {
    setStarting(true);
    onStartCall();
  };

  return (
    <main className="min-h-screen bg-[#07120f] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 md:px-10">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-400 text-xl font-black text-[#07120f]">
              ₹
            </div>

            <div>
              <p className="text-lg font-bold tracking-tight">
                BharatMoney
              </p>
              <p className="text-xs text-emerald-200/70">
                Voice AI · Financial Services
              </p>
            </div>
          </div>

          <div className="rounded-full border border-emerald-300/20 bg-emerald-300/5 px-3 py-1.5 text-xs text-emerald-100">
            🇮🇳 Built for Bharat
          </div>
        </header>

        <section className="flex flex-1 items-center justify-center py-12">
          <div className="w-full max-w-3xl text-center">
            <div className="mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-full border border-emerald-300/20 bg-emerald-300/10 shadow-[0_0_80px_rgba(52,211,153,0.12)]">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-400 text-3xl font-black text-[#07120f]">
                ₹
              </div>
            </div>

            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-emerald-300">
              Your voice financial companion
            </p>

            <h1 className="text-4xl font-black tracking-tight sm:text-5xl md:text-6xl">
              Meet BharatMoney
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-white/65 sm:text-lg">
              Ask questions about savings, budgeting, UPI, loans, EMI, and
              digital payment safety — in English, Hindi, or Hinglish.
            </p>

            <div className="mx-auto mt-8 grid max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                ['₹', 'Money Basics'],
                ['↗', 'UPI Safety'],
                ['✓', 'Simple Guidance'],
              ].map(([icon, label]) => (
                <div
                  key={label}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                >
                  <div className="text-xl text-emerald-300">{icon}</div>
                  <p className="mt-2 text-sm font-semibold">{label}</p>
                </div>
              ))}
            </div>

            <div className="mt-9 flex flex-col items-center">
              <Button
                size="lg"
                disabled={starting}
                onClick={handleStart}
                className="h-14 w-full max-w-sm rounded-full bg-emerald-400 px-8 text-sm font-bold text-[#07120f] hover:bg-emerald-300"
              >
                {starting ? 'Connecting…' : startButtonText || 'Start Talking'}
              </Button>

              <p className="mt-4 text-xs text-white/40">
                🎙️ Microphone access is required for the voice conversation.
              </p>
            </div>
          </div>
        </section>

        <footer className="border-t border-white/10 py-5 text-center text-xs text-white/35">
          BharatMoney provides financial education and general guidance.
          Never share your OTP, PIN, password, or CVV.
        </footer>
      </div>
    </main>
  );
};