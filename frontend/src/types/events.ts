import { Message } from './message';

export interface MessageEvent {
  type: 'Message';
  message: Message;
}

export interface ErrorEvent {
  type: 'Error';
  error: string;
}

export interface FinishEvent {
  type: 'Finish';
  reason: string;
}

export interface PingEvent {
  type: 'Ping';
}

export type SSEEvent = MessageEvent | ErrorEvent | FinishEvent | PingEvent;
