import { NextResponse } from 'next/server';
import {
  AccessToken,
  type AccessTokenOptions,
  type VideoGrant,
} from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;
const AGENT_NAME = process.env.AGENT_NAME;

export const revalidate = 0;

export async function POST(req: Request) {
  try {
    if (!API_KEY) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }

    if (!API_SECRET) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }

    if (!LIVEKIT_URL) {
      throw new Error('LIVEKIT_URL is not defined');
    }

    const body = await req.json().catch(() => ({}));

    const roomName =
      body?.room_name ||
      `voice_assistant_room_${Math.floor(Math.random() * 10000)}`;

    /*
     * IMPORTANT:
     * Same identity on every demo call so Day 4 memory
     * can recognize the same caller.
     */
    const participantIdentity = 'bharatmoney-demo-danish';
    const participantName = 'Danish';

    let roomConfig: RoomConfiguration | undefined;

    if (body?.room_config) {
      roomConfig = RoomConfiguration.fromJson(
        body.room_config,
        {
          ignoreUnknownFields: true,
        }
      );
    } else if (AGENT_NAME) {
      roomConfig = RoomConfiguration.fromJson(
        {
          agents: [
            {
              agentName: AGENT_NAME,
            },
          ],
        },
        {
          ignoreUnknownFields: true,
        }
      );
    }

    const participantToken = await createParticipantToken(
      {
        identity: participantIdentity,
        name: participantName,
      },
      roomName,
      roomConfig
    );

    /*
     * IMPORTANT:
     * Keep the response format expected by your existing
     * frontend ConnectionDetails interface.
     */
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantName,
      participantToken,
    };

    return NextResponse.json(
      data,
      {
        status: 200,
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );

  } catch (error) {
    console.error('LiveKit token error:', error);

    return new NextResponse(
      error instanceof Error
        ? error.message
        : 'Failed to create LiveKit token',
      {
        status: 500,
      }
    );
  }
}


function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomConfig?: RoomConfiguration
): Promise<string> {

  const at = new AccessToken(
    API_KEY!,
    API_SECRET!,
    {
      ...userInfo,
      ttl: '15m',
    }
  );

  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };

  at.addGrant(grant);

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();
}