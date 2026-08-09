'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import {
  useAgent,
  useSessionContext,
  useSessionMessages,
  useVoiceAssistant,
} from '@livekit/components-react';

import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({
  top = false,
  bottom = false,
  className,
}: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  className?: string;
}

export function AgentSessionView_01({
  preConnectMessage =
    'BharatMoney is ready. Ask me a financial question.',
  supportsChatInput = true,
  supportsVideoInput = true,
  supportsScreenShare = true,
  isPreConnectBufferEnabled = true,

  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,

  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const { state: agentState } = useAgent();
  const { state: voiceState } = useVoiceAssistant();

  const [chatOpen, setChatOpen] = useState(false);

  const scrollAreaRef = useRef<HTMLDivElement | null>(null);

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop =
        scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const stateConfig = {
    connecting: {
      label: 'Connecting to BharatMoney...',
      dot: 'bg-amber-400 animate-pulse',
      text: 'text-amber-300',
    },
    listening: {
      label: 'Listening to you',
      dot: 'bg-emerald-400 animate-pulse',
      text: 'text-emerald-300',
    },
    speaking: {
      label: 'BharatMoney is speaking',
      dot: 'bg-sky-400 animate-pulse',
      text: 'text-sky-300',
    },
    disconnected: {
      label: 'Call ended',
      dot: 'bg-red-400',
      text: 'text-red-300',
    },
  } as const;

  const currentState =
    stateConfig[voiceState as keyof typeof stateConfig] ??
    stateConfig.connecting;

  /*
   * IMPORTANT:
   * Do NOT call session.end() automatically here.
   *
   * The previous:
   *
   *   onDisconnect={session.end}
   *
   * could cause the frontend to terminate the session during
   * the connection lifecycle.
   *
   * The actual Leave button remains available through the
   * AgentControlBar.
   */
  const handleDisconnect = () => {
    console.log(
      '[BharatMoney] LiveKit disconnect callback received'
    );
  };

  return (
    <section
      ref={ref}
      className={cn(
        'bg-background relative z-10 h-full w-full overflow-hidden',
        className
      )}
      {...props}
    >
      {/* BharatMoney Header */}
      <header className="absolute left-0 right-0 top-0 z-50 flex items-center justify-between px-5 py-4 md:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-emerald-300/20 bg-emerald-300/10 text-lg">
            ₹
          </div>

          <div>
            <p className="text-sm font-bold text-white">
              BharatMoney
            </p>

            <p className="text-[10px] text-emerald-200/60">
              Financial Services Voice AI
            </p>
          </div>
        </div>

        <div className="rounded-full border border-emerald-300/20 bg-emerald-300/5 px-3 py-1 text-[10px] text-emerald-100">
          VoiceForBharat
        </div>
      </header>

      {/* Current Agent State */}
      <div className="absolute left-1/2 top-20 z-[70] -translate-x-1/2">
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-4 py-2 text-xs font-semibold shadow-lg backdrop-blur-md">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              currentState.dot
            )}
          />

          <span className={currentState.text}>
            {currentState.label}
          </span>
        </div>
      </div>

      {/* LiveKit Visualizer */}
      <TileLayout
        chatOpen={chatOpen}
        audioVisualizerType={audioVisualizerType}
        audioVisualizerColor={audioVisualizerColor}
        audioVisualizerColorShift={audioVisualizerColorShift}
        audioVisualizerBarCount={audioVisualizerBarCount}
        audioVisualizerRadialBarCount={
          audioVisualizerRadialBarCount
        }
        audioVisualizerRadialRadius={
          audioVisualizerRadialRadius
        }
        audioVisualizerGridRowCount={
          audioVisualizerGridRowCount
        }
        audioVisualizerGridColumnCount={
          audioVisualizerGridColumnCount
        }
        audioVisualizerWaveLineWidth={
          audioVisualizerWaveLineWidth
        }
      />

      {/* Transcript */}
      <div className="absolute bottom-[135px] top-0 flex w-full flex-col md:bottom-[170px]">
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out"
            >
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-2xl [&_.is-user>div]:rounded-[22px] [&>div>div]:px-4 [&>div>div]:pt-40 md:[&>div>div]:px-6"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom Controls */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {/* Status message */}
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="pointer-events-none mx-auto block w-full max-w-2xl pb-4 text-center text-sm font-semibold"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}

        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade
            bottom
            className="absolute inset-x-0 top-0 h-4 -translate-y-full"
          />

          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={handleDisconnect}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}