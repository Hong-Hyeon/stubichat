import { auth, type UserType } from '@/app/(auth)/auth';
import { BACKEND_CHAT_ENDPOINT } from '@/lib/constants';
import { postRequestBodySchema, type PostRequestBody } from './schema';
import { ChatSDKError } from '@/lib/errors';

export const maxDuration = 60;

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (_) {
    return new ChatSDKError('bad_request:api').toResponse();
  }

  try {
    const { id, message, selectedChatModel, selectedVisibilityType } = requestBody;

    const session = await auth();

    if (!session?.user) {
      return new ChatSDKError('unauthorized:chat').toResponse();
    }

    // Prepare request for backend
    const backendRequest = {
      id,
      message,
      selectedChatModel,
      selectedVisibilityType,
      user: {
        id: session.user.id,
        type: session.user.type,
      }
    };

    // Forward request to backend
    const backendResponse = await fetch(BACKEND_CHAT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendRequest),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return new Response(
        JSON.stringify({ error: errorData.detail || 'Backend request failed' }),
        { 
          status: backendResponse.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Return the backend response as a stream
    return new Response(backendResponse.body, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
      },
    });

  } catch (error) {
    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }
    
    console.error('Chat API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

export async function GET(request: Request) {
  // Handle resume requests if needed
  return new Response(null, { status: 204 });
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return new Response(
      JSON.stringify({ error: 'Chat ID is required' }),
      { 
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }

  try {
    const session = await auth();

    if (!session?.user) {
      return new ChatSDKError('unauthorized:chat').toResponse();
    }

    // Forward delete request to backend
    const backendResponse = await fetch(`${BACKEND_CHAT_ENDPOINT}?id=${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return new Response(
        JSON.stringify({ error: errorData.detail || 'Backend delete failed' }),
        { 
          status: backendResponse.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    return new Response(null, { status: 204 });

  } catch (error) {
    console.error('Delete chat error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
