import { Message } from '../types/message';

interface Props {
  message: Message;
}

export function UserMessage({ message }: Props) {
  const text = message.content
    .filter((c) => c.type === 'text')
    .map((c) => c.text)
    .join('\n');

  return (
    <div className="message user-message">
      <div className="message-body">
        <p>{text}</p>
      </div>
      <div className="message-avatar user-avatar">U</div>
    </div>
  );
}
